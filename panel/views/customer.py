from rest_framework import generics
from ..serializers.customer import CustomerSerializer
from panel.middleware import AdminSessionMiddleware
from customer.models import  Customer
from panel.permissions import IsAdminAuthenticated

class CustomerAdminListView(generics.ListAPIView):
    permission_classes = [IsAdminAuthenticated]
    authentication_classes = [AdminSessionMiddleware]
    serializer_class = CustomerSerializer
    queryset = Customer.objects.all()