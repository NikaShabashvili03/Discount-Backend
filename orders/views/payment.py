import base64
import json
import logging
import uuid
from decimal import Decimal

import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from django.conf import settings
from django.template.loader import render_to_string
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from customer.permissions import IsCustomerAuthenticated
from customer.middleware import CustomerSessionMiddleware
from orders.models import Order
from ..models.payment import Payment, PAYMENT_METHODS
from ..serializers.payment import PaymentSerializer

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

logger = logging.getLogger("orders.payment")


def _safe_response_body(response):
    """Return BOG response body as JSON dict if parseable, else raw text snippet.
    Used so we can log/return BOG's actual error reason even when it isn't JSON."""
    try:
        return response.json()
    except ValueError:
        text = (response.text or "")[:2000]
        return {"raw": text}


def _normalize_google_pay_token(raw):
    """Frontends pass the Google Pay token in different shapes depending on
    which API they used. BOG expects the contents of
    ``paymentMethodData.tokenizationData.token`` (a JSON string produced by the
    PAYMENT_GATEWAY tokenization spec) passed through verbatim.

    Accept any of:
      * the plain token string (most common)
      * the ``paymentMethodData`` dict
      * the full PaymentData dict ({paymentMethodData: {...}})
    Return the token string or None if no token could be located."""
    if raw is None:
        return None
    if isinstance(raw, str):
        return raw.strip() or None
    if isinstance(raw, dict):
        # PaymentData -> paymentMethodData.tokenizationData.token
        pmd = raw.get("paymentMethodData") or raw
        tok = (pmd.get("tokenizationData") or {}).get("token")
        if isinstance(tok, str) and tok.strip():
            return tok.strip()
        # Some clients post {"token": "..."} directly
        tok = raw.get("token")
        if isinstance(tok, str) and tok.strip():
            return tok.strip()
    return None


def _normalize_apple_pay_token(raw):
    """Apple Pay produces a ``PaymentToken`` object on the frontend:

        ApplePayPayment.token = {
            paymentData: { version, data, signature, header },
            paymentMethod: { ... },
            transactionIdentifier: "..."
        }

    BOG expects ``apple_pay_token`` to be the JSON-encoded ``paymentData``
    object (the encrypted blob). Accept the token in any of:
      * the plain JSON string the frontend already serialized
      * the ``paymentData`` dict (we JSON-encode it)
      * the full ``PaymentToken`` dict ({paymentData: {...}, ...})
      * the full ``ApplePayPayment`` dict ({token: {...}, ...})
    Return the JSON string or None if no token could be located."""
    if raw is None:
        return None
    if isinstance(raw, str):
        return raw.strip() or None
    if isinstance(raw, dict):
        # ApplePayPayment.token wrapper
        if isinstance(raw.get("token"), dict):
            raw = raw["token"]
        # PaymentToken.paymentData (the encrypted blob BOG wants)
        payment_data = raw.get("paymentData")
        if isinstance(payment_data, dict):
            return json.dumps(payment_data, separators=(",", ":"))
        if isinstance(payment_data, str) and payment_data.strip():
            return payment_data.strip()
        # Fallback: caller already shaped this as the payment-data dict itself.
        if {"version", "data", "signature"}.issubset(raw.keys()):
            return json.dumps(raw, separators=(",", ":"))
    return None

# -------------------------------
# BOG Authentication
# -------------------------------
def get_bog_access_token(client_id, client_secret):
    url = "https://oauth2.bog.ge/auth/realms/bog/protocol/openid-connect/token"
    auth_str = f"{client_id}:{client_secret}"
    base64_auth = base64.b64encode(auth_str.encode()).decode()

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {base64_auth}",
    }

    data = {"grant_type": "client_credentials"}

    response = requests.post(url, headers=headers, data=data, timeout=10)
    if response.status_code == 200:
        return response.json()["access_token"]
    logger.error("BOG token request failed status=%s body=%s",
                 response.status_code, (response.text or "")[:500])
    raise RuntimeError(f"Failed to get BOG token (status {response.status_code})")


# -------------------------------
# Initiate Payment
# -------------------------------
class BOGInitiatePaymentView(APIView):
    permission_classes = [IsCustomerAuthenticated]
    authentication_classes = [CustomerSessionMiddleware]

    def post(self, request):
        order_number = request.data.get("order_number")
        method = request.data.get("method")
        allowed_methods = [m[0] for m in PAYMENT_METHODS]

        if not order_number:
            return Response({"error": "order_number is required"}, status=400)

        if not method or method not in allowed_methods:
            return Response({"error": f"Invalid payment method. Allowed: {allowed_methods}"}, status=400)

        # Scope to the authenticated customer so one user cannot initiate
        # payments against another user's orders.
        try:
            order = Order.objects.get(order_number=order_number, customer=request.customer)
        except Order.DoesNotExist:
            return Response({"error": "Order not found."}, status=404)

        if order.status == "paid":
            return Response({"error": "Order already paid."}, status=400)

        # Get access token
        try:
            token = get_bog_access_token(settings.BOG_PUBLIC_KEY, settings.BOG_SECRET_KEY)
        except Exception as e:
            logger.exception("BOG auth failed for order %s", order_number)
            return Response({"error": "Failed to authenticate with BOG", "details": str(e)}, status=500)

        # Basket
        basket = [
            {
                "product_id": str(order.id),
                "description": order.event.description,
                "quantity": 1,
                "unit_price": float(order.total_price),
            }
        ]

        payload = {
            "callback_url": settings.BOG_CALLBACK_URL,
            "external_order_id": order.order_number,
            "application_type": "web",
            "purchase_units": {
                "currency": getattr(order, "currency", "GEL"),
                "total_amount": float(order.total_price),
                "basket": basket,
            },
            "redirect_urls": {
                "success": f"{settings.BOG_SUCCESS_URL}/{order_number}?status=success",
                "fail": f"{settings.BOG_FAIL_URL}/{order_number}?status=fail",
            },
            "payment_method": [method],
            "config": {
                "theme": "light",
                "capture": "automatic"
            },
            "buyer": {
                "full_name": order.customer_name,
                "masked_email": order.customer_email,
                "masked_phone": order.customer_phone,
            },
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "Accept-Language": "ka",
            "Idempotency-Key": str(uuid.uuid4()),
        }

        try:
            response = requests.post(
                f"{settings.BOG_BASE_URL}/payments/v1/ecommerce/orders",
                json=payload,
                headers=headers,
                timeout=10
            )
        except requests.RequestException:
            logger.exception("BOG initiate request failed for order %s", order_number)
            return Response({"error": "Failed to connect to BOG"}, status=502)

        response_data = _safe_response_body(response)

        if not (200 <= response.status_code < 300):
            logger.warning(
                "BOG initiate non-2xx order=%s method=%s status=%s body=%s",
                order_number, method, response.status_code, response_data,
            )
            return Response({"error": "Payment initiation failed", "details": response_data},
                            status=response.status_code)

        # Save payment record
        Payment.objects.update_or_create(
            order=order,
            defaults={
                "payment_method": method,
                "amount": order.total_price,
                "requested_amount": order.total_price,
                "currency": getattr(order, "currency", "GEL"),
                "transaction_id": response_data.get("id", ""),
                "payment_gateway_response": response_data,
                "capture_type": payload.get("config", {}).get("capture", "manual"),
            },
        )

        return Response(response_data, status=200)


# -------------------------------
# Initiate Google Pay Payment (external button on merchant site)
# -------------------------------
class BOGGooglePayInitiateView(APIView):
    """
    Initiates a BOG payment for an order paid with Google Pay via the
    merchant-hosted Google Pay button.

    The frontend renders the Google Pay button configured with:
        {
            "type": "PAYMENT_GATEWAY",
            "parameters": {
                "gateway": "georgiancard",
                "gatewayMerchantId": settings.BOG_GOOGLE_PAY_MERCHANT_ID
            }
        }
    and posts the resulting Google Pay token here.
    """
    permission_classes = [IsCustomerAuthenticated]
    authentication_classes = [CustomerSessionMiddleware]

    def post(self, request):
        order_number = request.data.get("order_number")
        raw_token = request.data.get("google_pay_token")

        if not order_number:
            return Response({"error": "order_number is required"}, status=400)

        google_pay_token = _normalize_google_pay_token(raw_token)
        if not google_pay_token:
            return Response(
                {"error": "google_pay_token is required",
                 "details": "Expected a Google Pay token string, the paymentMethodData "
                            "object, or the full PaymentData object."},
                status=400,
            )

        if not getattr(settings, "BOG_GOOGLE_PAY_MERCHANT_ID", ""):
            logger.error("BOG_GOOGLE_PAY_MERCHANT_ID is not configured; "
                         "Google Pay tokens generated for this merchant will be rejected.")
            return Response(
                {"error": "Google Pay is not configured on the server. "
                          "Set BOG_GOOGLE_PAY_MERCHANT_ID in the environment."},
                status=503,
            )

        # Scope to the authenticated customer so one user cannot pay against
        # another user's order.
        try:
            order = Order.objects.get(order_number=order_number, customer=request.customer)
        except Order.DoesNotExist:
            return Response({"error": "Order not found."}, status=404)

        if order.status == "paid":
            return Response({"error": "Order already paid."}, status=400)

        try:
            token = get_bog_access_token(settings.BOG_PUBLIC_KEY, settings.BOG_SECRET_KEY)
        except Exception as e:
            logger.exception("BOG auth failed for google-pay order %s", order_number)
            return Response({"error": "Failed to authenticate with BOG", "details": str(e)}, status=500)

        basket = [
            {
                "product_id": str(order.id),
                "description": order.event.description,
                "quantity": 1,
                "unit_price": float(order.total_price),
            }
        ]

        payload = {
            "callback_url": settings.BOG_CALLBACK_URL,
            "external_order_id": order.order_number,
            "application_type": "web",
            "purchase_units": {
                "currency": getattr(order, "currency", "GEL"),
                "total_amount": float(order.total_price),
                "basket": basket,
            },
            "redirect_urls": {
                "success": f"{settings.BOG_SUCCESS_URL}/{order_number}?status=success",
                "fail": f"{settings.BOG_FAIL_URL}/{order_number}?status=fail",
            },
            "payment_method": ["google_pay"],
            "config": {
                "theme": "light",
                "capture": "automatic",
                "google_pay": {
                    "external": True,
                    "google_pay_token": google_pay_token,
                },
            },
            "buyer": {
                "full_name": order.customer_name,
                "masked_email": order.customer_email,
                "masked_phone": order.customer_phone,
            },
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "Accept-Language": "ka",
            "Idempotency-Key": str(uuid.uuid4()),
        }

        try:
            response = requests.post(
                f"{settings.BOG_BASE_URL}/payments/v1/ecommerce/orders",
                json=payload,
                headers=headers,
                timeout=15,
            )
        except requests.RequestException:
            logger.exception("BOG google-pay initiate request failed for order %s", order_number)
            return Response({"error": "Failed to connect to BOG"}, status=502)

        response_data = _safe_response_body(response)

        if not (200 <= response.status_code < 300):
            # Log a payload preview WITHOUT the raw google_pay_token (PCI-adjacent data).
            safe_preview = {k: v for k, v in payload.items() if k != "config"}
            safe_preview["config"] = {
                **{k: v for k, v in payload["config"].items() if k != "google_pay"},
                "google_pay": {"external": True, "google_pay_token": "<redacted>"},
            }
            logger.warning(
                "BOG google-pay non-2xx order=%s status=%s body=%s payload=%s",
                order_number, response.status_code, response_data, safe_preview,
            )
            return Response({"error": "Payment initiation failed", "details": response_data},
                            status=response.status_code)

        Payment.objects.update_or_create(
            order=order,
            defaults={
                "payment_method": "google_pay",
                "amount": order.total_price,
                "requested_amount": order.total_price,
                "currency": getattr(order, "currency", "GEL"),
                "transaction_id": response_data.get("id", ""),
                "payment_gateway_response": response_data,
                "capture_type": payload.get("config", {}).get("capture", "manual"),
            },
        )

        return Response(response_data, status=200)


# -------------------------------
# Google Pay button configuration (for the frontend)
# -------------------------------
class BOGGooglePayConfigView(APIView):
    """
    Returns the tokenizationSpecification the frontend needs to render the
    Google Pay button so the gatewayMerchantId is not hard-coded in the JS.
    """
    permission_classes = [IsCustomerAuthenticated]
    authentication_classes = [CustomerSessionMiddleware]

    def get(self, request):
        merchant_id = getattr(settings, "BOG_GOOGLE_PAY_MERCHANT_ID", "")
        if not merchant_id:
            logger.error("BOG_GOOGLE_PAY_MERCHANT_ID is not set; Google Pay button cannot render.")
            return Response(
                {"error": "Google Pay is not configured on the server."},
                status=503,
            )
        return Response({
            "tokenization_specification": {
                "type": "PAYMENT_GATEWAY",
                "parameters": {
                    "gateway": "georgiancard",
                    "gatewayMerchantId": merchant_id,
                },
            },
        })


# -------------------------------
# Initiate Apple Pay Payment (external button on merchant site)
# -------------------------------
class BOGApplePayInitiateView(APIView):
    """
    Initiates a BOG payment for an order paid with Apple Pay via the
    merchant-hosted Apple Pay button.

    Per BOG docs, Apple Pay external is a TWO-STEP server flow (unlike
    Google Pay which is single-step):

      Step 1: POST /payments/v1/ecommerce/orders
              (payment_method=apple_pay, config.apple_pay.external=true,
              NO token yet) -> returns bog_order_id
      Step 2: POST /payments/v1/ecommerce/orders/{bog_order_id}/payment
              with {apple_pay_token: "..."} -> completes the charge

    This view does both calls server-side so the frontend POSTs once with
    {order_number, apple_pay_token} and gets back the final BOG response.
    """
    permission_classes = [IsCustomerAuthenticated]
    authentication_classes = [CustomerSessionMiddleware]

    def post(self, request):
        order_number = request.data.get("order_number")
        raw_token = request.data.get("apple_pay_token")

        if not order_number:
            return Response({"error": "order_number is required"}, status=400)

        apple_pay_token = _normalize_apple_pay_token(raw_token)
        if not apple_pay_token:
            return Response(
                {"error": "apple_pay_token is required",
                 "details": "Expected the Apple Pay PaymentToken — either the "
                            "JSON-stringified paymentData, the paymentData "
                            "object, or the full ApplePayPayment.token object."},
                status=400,
            )

        # Scope to the authenticated customer so one user cannot pay against
        # another user's order.
        try:
            order = Order.objects.get(order_number=order_number, customer=request.customer)
        except Order.DoesNotExist:
            return Response({"error": "Order not found."}, status=404)

        if order.status == "paid":
            return Response({"error": "Order already paid."}, status=400)

        try:
            token = get_bog_access_token(settings.BOG_PUBLIC_KEY, settings.BOG_SECRET_KEY)
        except Exception as e:
            logger.exception("BOG auth failed for apple-pay order %s", order_number)
            return Response({"error": "Failed to authenticate with BOG", "details": str(e)}, status=500)

        basket = [
            {
                "product_id": str(order.id),
                "description": order.event.description,
                "quantity": 1,
                "unit_price": float(order.total_price),
            }
        ]

        # --- Step 1: create the order on BOG (no token yet) ---
        create_payload = {
            "callback_url": settings.BOG_CALLBACK_URL,
            "external_order_id": order.order_number,
            "application_type": "web",
            "purchase_units": {
                "currency": getattr(order, "currency", "GEL"),
                "total_amount": float(order.total_price),
                "basket": basket,
            },
            "redirect_urls": {
                "success": f"{settings.BOG_SUCCESS_URL}/{order_number}?status=success",
                "fail": f"{settings.BOG_FAIL_URL}/{order_number}?status=fail",
            },
            "payment_method": ["apple_pay"],
            "config": {
                "theme": "light",
                "capture": "automatic",
                "apple_pay": {
                    "external": True,
                },
            },
            "buyer": {
                "full_name": order.customer_name,
                "masked_email": order.customer_email,
                "masked_phone": order.customer_phone,
            },
        }

        common_headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "Accept-Language": "ka",
        }

        try:
            create_response = requests.post(
                f"{settings.BOG_BASE_URL}/payments/v1/ecommerce/orders",
                json=create_payload,
                headers={**common_headers, "Idempotency-Key": str(uuid.uuid4())},
                timeout=15,
            )
        except requests.RequestException:
            logger.exception("BOG apple-pay create-order request failed for order %s",
                             order_number)
            return Response({"error": "Failed to connect to BOG"}, status=502)

        create_data = _safe_response_body(create_response)

        if not (200 <= create_response.status_code < 300):
            logger.warning(
                "BOG apple-pay create-order non-2xx order=%s status=%s body=%s",
                order_number, create_response.status_code, create_data,
            )
            return Response({"error": "Payment initiation failed (create step)",
                             "details": create_data},
                            status=create_response.status_code)

        bog_order_id = create_data.get("id")
        if not bog_order_id:
            logger.error("BOG apple-pay create-order returned no id order=%s body=%s",
                         order_number, create_data)
            return Response({"error": "Payment initiation failed (no order id)",
                             "details": create_data},
                            status=502)

        # --- Step 2: attach the encrypted Apple Pay token ---
        try:
            complete_response = requests.post(
                f"{settings.BOG_BASE_URL}/payments/v1/ecommerce/orders/{bog_order_id}/payment",
                json={"apple_pay_token": apple_pay_token},
                headers={**common_headers, "Idempotency-Key": str(uuid.uuid4())},
                timeout=15,
            )
        except requests.RequestException:
            logger.exception("BOG apple-pay complete request failed order=%s bog_id=%s",
                             order_number, bog_order_id)
            return Response({"error": "Failed to connect to BOG (complete step)",
                             "bog_order_id": bog_order_id},
                            status=502)

        complete_data = _safe_response_body(complete_response)

        if not (200 <= complete_response.status_code < 300):
            logger.warning(
                "BOG apple-pay complete non-2xx order=%s bog_id=%s status=%s body=%s",
                order_number, bog_order_id, complete_response.status_code, complete_data,
            )
            return Response({"error": "Payment completion failed",
                             "bog_order_id": bog_order_id,
                             "details": complete_data},
                            status=complete_response.status_code)

        Payment.objects.update_or_create(
            order=order,
            defaults={
                "payment_method": "apple_pay",
                "amount": order.total_price,
                "requested_amount": order.total_price,
                "currency": getattr(order, "currency", "GEL"),
                "transaction_id": complete_data.get("id", bog_order_id),
                "payment_gateway_response": complete_data,
                "capture_type": create_payload.get("config", {}).get("capture", "manual"),
            },
        )

        return Response(complete_data, status=200)


# -------------------------------
# Apple Pay button configuration (for the frontend)
# -------------------------------
class BOGApplePayConfigView(APIView):
    """
    Returns the Apple Pay merchant identifier + supported networks the
    frontend needs to start an ApplePaySession. Merchant certificate handling
    is done out-of-band with BOG; the frontend only needs the merchant ID and
    supported networks here.
    """
    permission_classes = [IsCustomerAuthenticated]
    authentication_classes = [CustomerSessionMiddleware]

    def get(self, request):
        merchant_id = getattr(settings, "BOG_APPLE_PAY_MERCHANT_ID", "")
        if not merchant_id:
            logger.error("BOG_APPLE_PAY_MERCHANT_ID is not set; Apple Pay button cannot render.")
            return Response(
                {"error": "Apple Pay is not configured on the server."},
                status=503,
            )
        return Response({
            "merchant_identifier": merchant_id,
            "supported_networks": ["visa", "masterCard", "amex"],
            "merchant_capabilities": ["supports3DS"],
            "country_code": "GE",
            "currency_code": "GEL",
        })


# -------------------------------
# BOG PUBLIC KEY
# -------------------------------
BOG_PUBLIC_KEY_PEM = """
-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAu4RUyAw3+CdkS3ZNILQh
zHI9Hemo+vKB9U2BSabppkKjzjjkf+0Sm76hSMiu/HFtYhqWOESryoCDJoqffY0Q
1VNt25aTxbj068QNUtnxQ7KQVLA+pG0smf+EBWlS1vBEAFbIas9d8c9b9sSEkTrr
TYQ90WIM8bGB6S/KLVoT1a7SnzabjoLc5Qf/SLDG5fu8dH8zckyeYKdRKSBJKvhx
tcBuHV4f7qsynQT+f2UYbESX/TLHwT5qFWZDHZ0YUOUIvb8n7JujVSGZO9/+ll/g
4ZIWhC1MlJgPObDwRkRd8NFOopgxMcMsDIZIoLbWKhHVq67hdbwpAq9K9WMmEhPn
PwIDAQAB
-----END PUBLIC KEY-----
"""


# -------------------------------
# CALLBACK FROM BOG
# -------------------------------
class BOGPaymentCallbackView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def verify_signature(self, raw_body, signature_base64):
        public_key_pem = BOG_PUBLIC_KEY_PEM
        try:
            signature = base64.b64decode(signature_base64)
            public_key = serialization.load_pem_public_key(public_key_pem.encode())
            public_key.verify(
                signature,
                raw_body,
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            return True
        except Exception:
            logger.warning("BOG callback signature verification failed.", exc_info=True)
            return False

    def _build_email_context(self, order: Order):
        """Shared context for the order_confirmation.html template."""
        currency = getattr(order, "currency", "GEL")
        event = getattr(order, "event", None)
        ticket_type = event.category.activity if event else "Unknown"
        event_name = event.name if event else "N/A"
    
        # Primary event image → absolute URL (blank if none).
        hero_image_url = ""
        if event is not None:
            primary = event.images.filter(is_primary=True).first()
            if primary and primary.image:
                try:
                    rel = primary.image.url
                except ValueError:
                    rel = ""
                if rel:
                    if rel.startswith("http://") or rel.startswith("https://"):
                        hero_image_url = rel
                    else:
                        site = getattr(settings, "SITE_URL", "https://funfinder.ge").rstrip("/")
                        hero_image_url = f"{site}{rel}"

        location_name = ""
        location_address = ""
        if event is not None:
            location_name = getattr(getattr(event, "city", None), "name", "") or ""
            location_address = getattr(event, "location", "") or ""

        event_datetime = ""
        if getattr(order, "event_date", None):
            event_datetime = order.event_date.strftime("%A<br>%B %d, %Y<br>%I:%M %p")

        order_year = order.created_at.year if getattr(order, "created_at", None) else 2026

        return {
            "customer_name": order.customer_name,
            "event_name": event_name,
            "artist_line": event_name,
            "location_name": location_name,
            "location_address": location_address,
            "event_datetime": event_datetime,
            "ticket_type": ticket_type,
            "quantity": str(order.people_count),
            "price": f"{order.total_price} {currency}",
            "ticket_id": order.order_number,
            "ticket_url": f"https://funfinder.ge/orders/{order.order_number}",
            "hero_image_url": hero_image_url,
            "year": str(order_year),
        }

    def _send_template_email(self, sg, sender_email, to_email, subject, ctx_overrides, base_ctx):
        ctx = {**base_ctx, **ctx_overrides, "subject": subject}
        html = render_to_string("email/order_confirmation.html", ctx)
        msg = Mail(
            from_email=sender_email,
            to_emails=to_email,
            subject=subject,
            html_content=html,
        )
        sg.send(msg)

    def send_success_email(self, order: Order):
        if not settings.SENDGRID_API_KEY:
            logger.info("SendGrid API Key not set, skipping email for order %s.",
                        order.order_number)
            return

        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        sender_email = settings.SENDGRID_EMAIL_SENDER

        base_ctx = self._build_email_context(order)
        event_name = base_ctx["event_name"]
        company_name = (
            order.event.company.name
            if getattr(order, "event", None) and getattr(order.event, "company", None)
            else "Unknown Company"
        )

        # Customer email
        try:
            self._send_template_email(
                sg,
                sender_email,
                order.customer_email,
                f"Your FunFinder ticket — {event_name}",
                {
                    "heading": "Order confirmation",
                    "intro": f"Thank you for your purchase, {order.customer_name}! Please save or print your ticket before the event.",
                    "hero_eyebrow": "Order confirmed",
                },
                base_ctx,
            )
        except Exception:
            logger.exception("Failed to send Customer email for order %s",
                             order.order_number)

        # Vendor/company email — recipient is configured via env so we don't
        # ship an internal address in source. Falls back to the company's own
        # email on the event when the override is not set.
        vendor_email = getattr(settings, "FUNFINDER_VENDOR_NOTIFICATION_EMAIL", "") or (
            order.event.company.email
            if getattr(order, "event", None) and getattr(order.event, "company", None)
            else ""
        )
        if vendor_email:
            try:
                self._send_template_email(
                    sg,
                    sender_email,
                    vendor_email,
                    f"New booking — {event_name}",
                    {
                        "heading": "New booking received",
                        "intro": f"Hello {company_name}, you have a new paid booking from {order.customer_name} via FunFinder.",
                        "hero_eyebrow": "New booking",
                    },
                    base_ctx,
                )
            except Exception:
                logger.exception("Failed to send Company email for order %s",
                                 order.order_number)

        # Admin email — recipient configured via env (FUNFINDER_ADMIN_EMAIL).
        admin_email = getattr(settings, "FUNFINDER_ADMIN_EMAIL", "")
        if admin_email:
            try:
                self._send_template_email(
                    sg,
                    sender_email,
                    admin_email,
                    f"[ADMIN] New transaction #{order.order_number}",
                    {
                        "heading": "New transaction",
                        "intro": f"Payment processed for {order.customer_name} ({order.customer_email}) — vendor: {company_name}.",
                        "hero_eyebrow": "Admin alert",
                    },
                    base_ctx,
                )
                logger.info("All emails processed for Order #%s", order.order_number)
            except Exception:
                logger.exception("Failed to send Admin email for order %s",
                                 order.order_number)
        else:
            logger.info("FUNFINDER_ADMIN_EMAIL not configured; skipping admin email "
                        "for order %s.", order.order_number)
            
    def post(self, request, *args, **kwargs):
        raw_body = request.body
        callback_signature = request.headers.get("Callback-Signature")

        # Signature is mandatory: an unsigned callback is treated as forged.
        # Previously this check was `if callback_signature and not verify`, which
        # silently skipped verification when the header was absent — letting
        # anyone POST a fake "paid" payload.
        if not callback_signature or not self.verify_signature(raw_body, callback_signature):
            logger.warning("BOG callback rejected: missing or invalid signature.")
            return Response({"error": "Invalid signature"}, status=400)

        try:
            data = json.loads(raw_body)
        except Exception:
            logger.warning("BOG callback: invalid JSON body received.")
            return Response({"error": "Invalid JSON"}, status=400)

        body = data.get("body", {})
        logger.info("BOG callback received: %s", body)

        external_order_id = body.get("external_order_id") or body.get("order_id")

        if not external_order_id:
            return Response({"error": "Order ID missing"}, status=400)

        try:
            order = Order.objects.get(order_number=external_order_id)
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=404)

        payment_detail = body.get("payment_detail", {})
        transaction_id = payment_detail.get("transaction_id", "")

        purchase_units = body.get("purchase_units", {}) or {}
        transfer_amount = purchase_units.get("transfer_amount") or "0"
        amount = Decimal(transfer_amount)

        bog_status = body.get("order_status", {}).get("key", "pending")

        status_map = {
            "completed": "paid",
            "processing": "processing",
            "created": "pending",
            "rejected": "failed",
            "refund_requested": "refund_requested",
            "refunded": "refunded",
            "refunded_partially": "refunded",
            "partial_completed": "partial_paid",
            "blocked": "blocked",
            "auth_requested": "auth_requested",
        }

        internal_status = status_map.get(bog_status, "pending")

        if internal_status == "paid" and order.status != "paid":
            self.send_success_email(order)

        order.status = internal_status
        order.save()

        method_key = payment_detail.get("transfer_method", {}).get("key", "")
        card_type = payment_detail.get("card_type", "")
        payer_identifier = payment_detail.get("payer_identifier", "")
        result_code = payment_detail.get("code", "")
        result_message = payment_detail.get("code_description", "")

        Payment.objects.update_or_create(
            order=order,
            defaults={
                "payment_method": method_key or "card",
                "amount": amount,
                "requested_amount": order.total_price,
                "currency": getattr(order, "currency", "GEL"),
                "transaction_id": transaction_id,
                "status": internal_status,
                "method_provider": method_key,
                "card_type": card_type,
                "payer_identifier": payer_identifier,
                "result_code": result_code,
                "result_message": result_message,
                "payment_gateway_response": data,
            },
        )

        return Response({"message": "Callback processed"}, status=200)


# -------------------------------
# CHECK PAYMENT STATUS / RECEIPT
# -------------------------------
class BOGPaymentStatusView(APIView):
    permission_classes = [IsCustomerAuthenticated]
    authentication_classes = [CustomerSessionMiddleware]

    def get(self, request, order_id):
        # Scope to the authenticated customer — payment receipts are personal data.
        try:
            order = (
                Order.objects
                .select_related("payment")
                .get(order_number=order_id, customer=request.customer)
            )
        except Order.DoesNotExist:
            return Response(
                {"success": False, "message": "Order not found."},
                status=404
            )

        payment = getattr(order, "payment", None)
        if payment is None:
            return Response(
                {"success": False, "message": "Payment record not found."},
                status=404
            )

        return Response(PaymentSerializer(payment).data)
    
# -------------------------------
# CHECK PAYMENT STATUS / RECEIPT
# -------------------------------
# class BOGPaymentStatusView(APIView):
#     authentication_classes = []
#     permission_classes = [permissions.AllowAny]

#     def get(self, request, transaction_id):
#         try:
#             token = get_bog_access_token(settings.BOG_PUBLIC_KEY, settings.BOG_SECRET_KEY)
#         except Exception as e:
#             return Response({"error": "Failed to authenticate with BOG", "details": str(e)}, status=500)

#         headers = {
#             "Content-Type": "application/json",
#             "Authorization": f"Bearer {token}",
#         }

#         try:
#             response = requests.get(
#                 f"{settings.BOG_BASE_URL}/payments/v1/receipt/{transaction_id}",
#                 headers=headers,
#                 timeout=10,
#             )
#             return Response(response.json(), status=response.status_code)
#         except Exception as e:
#             return Response({"error": "Failed to fetch payment status", "details": str(e)}, status=500)
