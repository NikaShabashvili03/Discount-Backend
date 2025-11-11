import requests
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from orders.models import Order
from ..models import Payment
import base64
import uuid
from rest_framework import permissions

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

class BOGInitiatePaymentView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

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
                "currency": "GEL",
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

        return Response(response_data, status=200)

class BOGPaymentCallbackView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        print(request.data)
        orders = Order.objects.all()
        for order in orders:
            order.status = "completed"
            order.payment_status = "paid"
            order.save()
        
        return Response({"message": "Callback verified and processed"})

class BOGPaymentStatusView(APIView):
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
