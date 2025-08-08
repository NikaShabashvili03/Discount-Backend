from django.urls import path, include

urlpatterns = [
    path('order/', include('orders.urls.order')),
    path('payment/', include('orders.urls.payment'))
]