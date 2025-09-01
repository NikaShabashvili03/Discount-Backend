from ..serializers.order import OrderCreateSerializer, OrderSerializer
from ..models import Order
from rest_framework import generics, permissions
from accounts.permissions import IsCustomerAuthenticated
from accounts.middleware import CustomerSessionMiddleware
    

class OrderCreateView(generics.CreateAPIView):
    serializer_class = OrderCreateSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = [CustomerSessionMiddleware]
    
    def perform_create(self, serializer):
        serializer.save()

class OrderListView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsCustomerAuthenticated]
    authentication_classes = [CustomerSessionMiddleware]
    
    def get_queryset(self):
        user = self.request.customer
        return Order.objects.filter(customer=user)

class OrderDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsCustomerAuthenticated]
    authentication_classes = [CustomerSessionMiddleware]
    
    def get_queryset(self):
        user = self.request.customer
        return Order.objects.filter(customer=user)