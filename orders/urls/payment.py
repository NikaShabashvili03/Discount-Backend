# orders/urls/payment.py
from django.urls import path
from orders.views.payment import (
    BOGInitiatePaymentView,
    BOGPaymentCallbackView,
    BOGPaymentStatusView
)

urlpatterns = [
    path('bog/initiate', BOGInitiatePaymentView.as_view(), name='bog-initiate'),
    path('bog/callback', BOGPaymentCallbackView.as_view(), name='bog-callback'),
    path('bog/status/<str:order_id>', BOGPaymentStatusView.as_view(), name='bog-status'),
]
