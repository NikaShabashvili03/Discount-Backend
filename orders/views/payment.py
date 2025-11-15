import base64
import json
import uuid
from decimal import Decimal

import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from django.conf import settings
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from customer.permissions import IsCustomerAuthenticated
from customer.middleware import CustomerSessionMiddleware
from orders.models import Order
from ..models.payment import Payment, PAYMENT_METHODS
from ..serializers.payment import PaymentSerializer

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

    response = requests.post(url, headers=headers, data=data)
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        raise Exception(f"Failed to get BOG token: {response.text}")


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

        try:
            order = Order.objects.get(order_number=order_number)
        except Order.DoesNotExist:
            return Response({"error": "Order not found."}, status=404)

        if order.status == "paid":
            return Response({"error": "Order already paid."}, status=400)

        # Get access token
        try:
            token = get_bog_access_token(settings.BOG_PUBLIC_KEY, settings.BOG_SECRET_KEY)
        except Exception as e:
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
            response_data = response.json()
        except Exception:
            return Response({"error": "Failed to connect to BOG"}, status=500)

        if not (200 <= response.status_code < 300):
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
        signature = base64.b64decode(signature_base64)

        public_key = serialization.load_pem_public_key(public_key_pem.encode())
        try:
            public_key.verify(
                signature,
                raw_body,
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            return True
        except Exception:
            return False

    def post(self, request, *args, **kwargs):
        raw_body = request.body
        callback_signature = request.headers.get("Callback-Signature")

        if callback_signature and not self.verify_signature(raw_body, callback_signature):
            return Response({"error": "Invalid signature"}, status=400)

        try:
            data = json.loads(raw_body)
        except Exception:
            return Response({"error": "Invalid JSON"}, status=400)

        body = data.get("body", {})
        print("BOG CALLBACK:", body)

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
        try:
            order = (
                Order.objects
                .select_related("payment") 
                .get(order_number=order_id)
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
