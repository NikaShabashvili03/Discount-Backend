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

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

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

    def send_success_email(self, order: Order):
        if not settings.SENDGRID_API_KEY:
            print("SendGrid API Key not set, skipping email.")
            return

        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        sender_email = settings.SENDGRID_EMAIL_SENDER

        currency = getattr(order, 'currency', 'GEL')
        event_name = order.event.description if hasattr(order, 'event') else 'N/A'
        company_name = order.event.company.name if hasattr(order, 'event') and hasattr(order.event, 'company') else 'Unknown Company'
        

        subject_customer = f"Payment Successful - Order #{order.order_number}"
        html_customer = f"""
            <html>
                <body style="font-family: Arial, sans-serif; color: #333;">
                    <h2 style="color: #4CAF50;">Payment Successful!</h2>
                    <p>Dear {order.customer_name},</p>
                    <p>Thank you for your payment. Your order has been successfully processed.</p>
                    
                    <table style="width: 100%; max-width: 600px; border-collapse: collapse; margin-top: 20px;">
                        <tr style="background-color: #f9f9f9;">
                            <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">Order Number</th>
                            <td style="padding: 10px; border: 1px solid #ddd;">{order.order_number}</td>
                        </tr>
                        <tr>
                            <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">Amount Paid</th>
                            <td style="padding: 10px; border: 1px solid #ddd;">{order.total_price} {currency}</td>
                        </tr>
                        <tr style="background-color: #f9f9f9;">
                            <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">Event</th>
                            <td style="padding: 10px; border: 1px solid #ddd;">{event_name}</td>
                        </tr>
                    </table>
                    <p style="margin-top: 20px;">We hope you have a great time!</p>
                </body>
            </html>
        """
        
        try:
            msg_customer = Mail(
                from_email=sender_email,
                to_emails=order.customer_email,
                subject=subject_customer,
                html_content=html_customer
            )
            sg.send(msg_customer)
        except Exception as e:
            print(f"Failed to send Customer email: {str(e)}")


        if hasattr(order, 'event') and hasattr(order.event, 'company') and order.event.company.email:
            subject_company = f"New Order Received - Order #{order.order_number}"
            html_company = f"""
                <html>
                    <body style="font-family: Arial, sans-serif; color: #333;">
                        <h2 style="color: #2196F3;">New Order Received</h2>
                        <p>Hello {company_name},</p>
                        <p>Good news! You have received a new booking/order via FunFinder.</p>
                        
                        <table style="width: 100%; max-width: 600px; border-collapse: collapse; margin-top: 20px;">
                            <tr style="background-color: #f9f9f9;">
                                <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">Product/Event</th>
                                <td style="padding: 10px; border: 1px solid #ddd;">{event_name}</td>
                            </tr>
                            <tr>
                                <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">Customer Name</th>
                                <td style="padding: 10px; border: 1px solid #ddd;">{order.customer_name}</td>
                            </tr>
                            <tr style="background-color: #f9f9f9;">
                                <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">Customer Email</th>
                                <td style="padding: 10px; border: 1px solid #ddd;">{order.customer_email}</td>
                            </tr>
                            <tr>
                                <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">Order Total</th>
                                <td style="padding: 10px; border: 1px solid #ddd;">{order.total_price} {currency}</td>
                            </tr>
                        </table>
                        <p style="margin-top: 20px;">Please check your dashboard for more details.</p>
                    </body>
                </html>
            """
            
            try:
                msg_company = Mail(
                    from_email=sender_email,
                    to_emails="i.diasamidze@funfinder.ge", # "order.event.company.email"
                    subject=subject_company,
                    html_content=html_company
                )
                sg.send(msg_company)
            except Exception as e:
                print(f"Failed to send Company email: {str(e)}")


        subject_admin = f"[ADMIN] New Transaction - #{order.order_number}"
        html_admin = f"""
            <html>
                <body style="font-family: Arial, sans-serif; color: #333;">
                    <h2 style="color: #FF9800;">New Transaction Alert</h2>
                    <p>A new payment has been successfully processed.</p>
                    
                    <table style="width: 100%; max-width: 600px; border-collapse: collapse; margin-top: 20px;">
                        <tr style="background-color: #f2f2f2;">
                            <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">Order ID</th>
                            <td style="padding: 10px; border: 1px solid #ddd;">{order.order_number}</td>
                        </tr>
                        <tr>
                            <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">Customer</th>
                            <td style="padding: 10px; border: 1px solid #ddd;">{order.customer_name} ({order.customer_email})</td>
                        </tr>
                        <tr style="background-color: #f2f2f2;">
                            <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">Vendor</th>
                            <td style="padding: 10px; border: 1px solid #ddd;">{company_name}</td>
                        </tr>
                        <tr>
                            <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">Amount</th>
                            <td style="padding: 10px; border: 1px solid #ddd;">{order.total_price} {currency}</td>
                        </tr>
                        <tr style="background-color: #f2f2f2;">
                            <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">Timestamp</th>
                            <td style="padding: 10px; border: 1px solid #ddd;">{order.created_at if hasattr(order, 'created_at') else 'Now'}</td>
                        </tr>
                    </table>
                </body>
            </html>
        """
        
        try:
            msg_admin = Mail(
                from_email=sender_email,
                to_emails='funfinder.ge@gmail.com',
                subject=subject_admin,
                html_content=html_admin
            )
            sg.send(msg_admin)
            print(f"All emails processed for Order #{order.order_number}")
        except Exception as e:
            print(f"Failed to send Admin email: {str(e)}")
            
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
