from django.urls import path
from orders.views.payment import BOGInitiatePaymentView, BOGPaymentCallbackView

urlpatterns = [
    path('bog/initiate/', BOGInitiatePaymentView.as_view(), name='bog-initiate'),
    path('bog/callback/', BOGPaymentCallbackView.as_view(), name='bog-callback'),
]

   