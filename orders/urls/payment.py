# orders/urls/payment.py
from django.urls import path
from orders.views.payment import (
    BOGInitiatePaymentView,
    BOGPaymentCallbackView,
    BOGPaymentStatusView,
    BOGGooglePayInitiateView,
    BOGGooglePayConfigView,
)

urlpatterns = [
    path('bog/initiate', BOGInitiatePaymentView.as_view(), name='bog-initiate'),
    path('bog/callback', BOGPaymentCallbackView.as_view(), name='bog-callback'),
    path('bog/status/<str:order_id>', BOGPaymentStatusView.as_view(), name='bog-status'),
    path('bog/google-pay/config', BOGGooglePayConfigView.as_view(), name='bog-google-pay-config'),
    path('bog/google-pay/initiate', BOGGooglePayInitiateView.as_view(), name='bog-google-pay-initiate'),
]
