from ..serializers.order import OrderCreateSerializer, OrderSerializer
from ..models import Order
from rest_framework import generics, permissions


class OrderCreateView(generics.CreateAPIView):
    serializer_class = OrderCreateSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    
    def perform_create(self, serializer):
        serializer.save()

class OrderListView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'customer':
            return Order.objects.filter(customer=user)
        elif user.user_type == 'provider':
            return Order.objects.filter(service__provider__user=user)
        return Order.objects.none()

class OrderDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'customer':
            return Order.objects.filter(customer=user)
        elif user.user_type == 'provider':
            return Order.objects.filter(service__provider__user=user)
        return Order.objects.none()