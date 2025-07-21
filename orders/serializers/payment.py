from .order import OrderSerializer
from ..models import Payment
from rest_framework import serializers

class PaymentSerializer(serializers.ModelSerializer):
    order = OrderSerializer(read_only=True)
    
    class Meta:
        model = Payment
        fields = ['id', 'order', 'payment_method', 'amount', 'currency', 'transaction_id', 'created_at']
        read_only_fields = ['id', 'created_at']