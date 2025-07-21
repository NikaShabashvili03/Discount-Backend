from django.urls import path
from orders.views.order import OrderCreateView, OrderDetailView, OrderListView

urlpatterns = [
    path('feed', OrderListView.as_view(), name='order-list'),
    path('create', OrderCreateView.as_view(), name='order-create'),
    path('details/<int:pk>', OrderDetailView.as_view(), name='order-detail'),
]

   