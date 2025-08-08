# payments/views.py
import requests
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from orders.models import Order
from ..models import Payment


class BOGInitiatePaymentView(APIView):
    def post(self, request):
        order_id = request.data.get("order_id")
        payment_method = request.data.get("payment_method", "bog")

        try:
            order = Order.objects.get(order_number=order_id)
        except Order.DoesNotExist:
            return Response({"error": "Order not found."}, status=404)

        if order.payment_status == 'paid':
            return Response({"error": "Order already paid."}, status=400)

        # Prepare request to BOG API
        payload = {
            "amount": str(order.total_price),
            "currency": order.currency if hasattr(order, 'currency') else "GEL",
            "callback_url": settings.BOG_REDIRECT_URL,
            "order_id": order.order_number,
            "description": f"Payment for order {order.order_number}",
        }

        headers = {
            "Authorization": f"Bearer {settings.BOG_API_KEY}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                f"{settings.BOG_BASE_URL}/payments/initiate",
                json=payload,
                headers=headers
            )
            response_data = response.json()

            # Save payment instance
            Payment.objects.create(
                order=order,
                payment_method=payment_method,
                amount=order.total_price,
                currency=payload['currency'],
                transaction_id=response_data.get("transaction_id", ""),
                payment_gateway_response=response_data
            )

            return Response(response_data, status=response.status_code)

        except Exception as e:
            return Response({"error": "Payment initiation failed.", "details": str(e)}, status=500)

class BOGPaymentCallbackView(APIView):
    def post(self, request):
        data = request.data
        order_id = data.get("order_id")
        transaction_id = data.get("transaction_id")
        status_code = data.get("status")

        try:
            order = Order.objects.get(order_number=order_id)
            payment = Payment.objects.get(order=order)
        except (Order.DoesNotExist, Payment.DoesNotExist):
            return Response({"error": "Order/payment not found."}, status=404)

        # Update based on BOG status
        if status_code == "SUCCESS":
            order.payment_status = 'paid'
            order.status = 'confirmed'
        elif status_code == "FAILED":
            order.payment_status = 'failed'
        order.save()

        payment.payment_gateway_response = data
        payment.transaction_id = transaction_id
        payment.save()

        return Response({"message": "Callback processed."}, status=200)
