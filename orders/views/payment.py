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

from orders.models import Order
from ..models.payment import Payment, PAYMENT_METHODS


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
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        order_number = request.data.get("order_number")
        method = request.data.get("method")  # Chosen payment method
        allowed_methods = [m[0] for m in PAYMENT_METHODS]

        if not order_number:
            return Response({"error": "order_number is required"}, status=400)

        if not method or method not in allowed_methods:
            return Response({"error": f"Invalid payment method. Allowed: {allowed_methods}"}, status=400)

        try:
            order = Order.objects.get(order_number=order_number)
        except Order.DoesNotExist:
            return Response({"error": "Order not found."}, status=404)

        if order.payment_status == "paid":
            return Response({"error": "Order already paid."}, status=400)

        # Get access token
        try:
            token = get_bog_access_token(settings.BOG_CLIENT_INN, settings.BOG_SECRET_KEY)
        except Exception as e:
            return Response({"error": "Failed to authenticate with BOG", "details": str(e)}, status=500)

        # Basket
        basket = [
            {
                "product_id": str(order.id),
                "description": order.event.name,
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
                "success": settings.BOG_SUCCESS_URL,
                "fail": settings.BOG_FAIL_URL,
            },
            "payment_method": [method],  # Use chosen method
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
            return Response({"error": "Payment initiation failed", "details": response_data}, status=response.status_code)

        # Save Payment
        Payment.objects.update_or_create(
            order=order,
            defaults={
                "payment_method": method,  # Save chosen method
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
# Callback with Signature Verification
# -------------------------------
class BOGPaymentCallbackView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def verify_signature(self, raw_body, signature_base64):
        """
        Verify BOG callback signature using SHA256withRSA
        """
        public_key_pem = settings.BOG_PUBLIC_KEY  # Use existing public key
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

        if callback_signature:
            if not self.verify_signature(raw_body, callback_signature):
                return Response({"error": "Invalid signature"}, status=400)

        data = json.loads(raw_body)
        body = data.get("body", {})

        external_order_id = body.get("order_id") or body.get("external_order_id")
        payment_detail = body.get("payment_detail", {})
        transaction_id = payment_detail.get("transaction_id")
        amount = Decimal(body.get("purchase_units", {}).get("transfer_amount", 0.0))

        if not external_order_id:
            return Response({"error": "Order ID not provided"}, status=400)

        try:
            order = Order.objects.get(order_number=external_order_id)
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=404)

        bog_status = body.get("order_status", {}).get("key", "pending")
        status_map = {
            "completed": ("completed", "paid"),
            "failed": ("cancelled", "failed"),
            "refunded": ("completed", "refunded"),
            "pending": ("pending", "pending"),
        }
        order.status, order.payment_status = status_map.get(bog_status, ("pending", "pending"))
        order.save()

        Payment.objects.update_or_create(
            order=order,
            defaults={
                "payment_method": order.payment.payment_method if hasattr(order, 'payment') else "bog",
                "amount": amount,
                "requested_amount": amount,
                "currency": getattr(order, "currency", "GEL"),
                "transaction_id": transaction_id or "",
                "payment_gateway_response": data,
            },
        )

        return Response({"message": "Payment callback processed successfully"}, status=200)


# -------------------------------
# Payment Status
# -------------------------------
class BOGPaymentStatusView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def get(self, request, transaction_id):
        try:
            token = get_bog_access_token(settings.BOG_CLIENT_INN, settings.BOG_SECRET_KEY)
        except Exception as e:
            return Response({"error": "Failed to authenticate with BOG", "details": str(e)}, status=500)

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }

        try:
            response = requests.get(
                f"{settings.BOG_BASE_URL}/payments/v1/ecommerce/orders/{transaction_id}",
                headers=headers,
                timeout=10,
            )
            return Response(response.json(), status=response.status_code)
        except Exception as e:
            return Response({"error": "Failed to fetch payment status", "details": str(e)}, status=500)
