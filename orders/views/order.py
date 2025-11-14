from ..serializers.order import OrderCreateSerializer, OrderSerializer
from ..models import Order
from rest_framework import generics, permissions
from customer.permissions import IsCustomerAuthenticated
from customer.middleware import CustomerSessionMiddleware
from rest_framework.response import Response

class OrderCreateView(generics.CreateAPIView):
    serializer_class = OrderCreateSerializer
    permission_classes = [IsCustomerAuthenticated]
    authentication_classes = [CustomerSessionMiddleware]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        order = serializer.save()
        
        detailed_data = OrderSerializer(order, context={'request': request}).data
        return Response(detailed_data, status=201)

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