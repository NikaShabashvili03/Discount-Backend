# orders/urls/payment.py
from django.urls import path
from orders.views.payment import (
    BOGInitiatePaymentView,
    BOGPaymentCallbackView,
    BOGPaymentStatusView,
    BOGGooglePayInitiateView,
    BOGGooglePayConfigView,
    BOGApplePayInitiateView,
    BOGApplePayConfigView,
)

urlpatterns = [
    path('bog/initiate', BOGInitiatePaymentView.as_view(), name='bog-initiate'),
    path('bog/callback', BOGPaymentCallbackView.as_view(), name='bog-callback'),
    path('bog/status/<str:order_id>', BOGPaymentStatusView.as_view(), name='bog-status'),
    path('bog/google-pay/config', BOGGooglePayConfigView.as_view(), name='bog-google-pay-config'),
    path('bog/google-pay/initiate', BOGGooglePayInitiateView.as_view(), name='bog-google-pay-initiate'),
    path('bog/apple-pay/config', BOGApplePayConfigView.as_view(), name='bog-apple-pay-config'),
    path('bog/apple-pay/initiate', BOGApplePayInitiateView.as_view(), name='bog-apple-pay-initiate'),
]
