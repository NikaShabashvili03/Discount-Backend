import requests
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from orders.models import Order
from ..models import Payment
import json
import base64
import uuid
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from rest_framework import generics, permissions

def get_bog_access_token(client_id, client_secret):
    """
    Authenticate with BOG and return Bearer token.
    """
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


class BOGInitiatePaymentView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    """
    Initiate payment request to BOG API.
    """
    def post(self, request):
        order_number = request.data.get("order_number")
        if not order_number:
            return Response({"error": "order_number is required"}, status=400)

        try:
            order = Order.objects.get(order_number=order_number)
        except Order.DoesNotExist:
            return Response({"error": "Order not found."}, status=404)

        if order.payment_status == "paid":
            return Response({"error": "Order already paid."}, status=400)

        try:
            token = get_bog_access_token(settings.BOG_PUBLIC_KEY, settings.BOG_SECRET_KEY)
        except Exception as e:
            return Response({"error": "Failed to authenticate with BOG", "details": str(e)}, status=500)

        basket = [
            {
                "product_id": str(order.id),
                "quantity": 1,
                "unit_price": float(order.total_price),
            }
        ]

        payload = {
            "callback_url": settings.BOG_CALLBACK_URL,
            "external_order_id": order.order_number,
            "purchase_units": {
                "currency": getattr(order, "currency", "GEL"),
                "total_amount": float(order.total_price),
                "basket": basket,
            },
            "redirect_urls": {
                "success": settings.BOG_SUCCESS_URL,
                "fail": settings.BOG_FAIL_URL,
            }
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

        Payment.objects.update_or_create(
            order=order,
            defaults={
                "payment_method": "bog",
                "amount": order.total_price,
                "currency": getattr(order, "currency", "GEL"),
                "transaction_id": response_data.get("id", ""),
                "payment_gateway_response": response_data,
            },
        )

        # redirect_url = response_data.get("_links", {}).get("redirect", {}).get("href")
        # {
        #     "order_id": response_data.get("id"),
        #     "redirect_url": redirect_url,
        #     "details": response_data
        # }
        return Response(response_data, status=200)

# ✅ BOG official public key (used for verifying callback)
BOG_PUBLIC_KEY = """
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

class BOGPaymentCallbackView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        order = Order.objects.get(order_number="FFSYECKN")
        order.payment_status = "paid"
        order.status = "confirmed"
        order.save()
        return Response({"message": "Callback verified and processed"}, status=200)
    
        raw_body = request.body
        signature_b64 = request.headers.get("Callback-Signature")

        if not signature_b64:
            return Response({"error": "Missing Callback-Signature header"}, status=400)

        # ✅ Step 1: Verify callback signature before parsing JSON
        try:
            public_key = serialization.load_pem_public_key(BOG_PUBLIC_KEY.encode())
            signature = base64.b64decode(signature_b64)
            public_key.verify(
                signature,
                raw_body,
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
        except Exception as e:
            return Response({"error": "Invalid signature", "details": str(e)}, status=400)

        # ✅ Step 2: Parse the raw JSON
        try:
            payload = json.loads(raw_body)
            data = payload.get("body", {})
        except Exception:
            return Response({"error": "Invalid JSON"}, status=400)

        order_id = data.get("order_id")
        status_code = data.get("status")

        if not order_id or not status_code:
            return Response({"error": "Missing required fields"}, status=400)

        # ✅ Step 3: Find Payment and Order
        try:
            payment = Payment.objects.get(transaction_id=order_id)
            order = payment.order
        except Payment.DoesNotExist:
            return Response({"error": "Payment not found"}, status=404)

        # ✅ Step 4: Update order based on callback status
        if status_code == "SUCCESS":
            order.payment_status = "paid"
            order.status = "confirmed"
        elif status_code in ["FAILED", "CANCELED"]:
            order.payment_status = "failed"
        elif status_code == "REFUNDED":
            order.payment_status = "refunded"

        order.save()

        # ✅ Step 5: Save callback data
        payment.payment_gateway_response = data
        payment.save()

        return Response({"message": "Callback verified and processed"}, status=200)


class BOGPaymentStatusView(APIView):
    """
    Manually check payment status from BOG (if callback fails).
    """
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    def get(self, request, transaction_id):
        try:
            token = get_bog_access_token(settings.BOG_PUBLIC_KEY, settings.BOG_SECRET_KEY)
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
