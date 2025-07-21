from rest_framework import serializers
from services.models import Service
from services.serializer.service import ServiceListSerializer
from accounts.serializers.user import UserSerializer
from ..models import Order
from decimal import Decimal

class OrderCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['service', 'customer_name', 'customer_email', 'customer_phone', 'customer_country',
                 'people_count', 'service_date', 'notes']
    
    def validate_people_count(self, value):
        service = self.initial_data.get('service')
        if service:
            try:
                service_obj = Service.objects.get(id=service)
                if value < service_obj.min_people or value > service_obj.max_people:
                    raise serializers.ValidationError(
                        f'People count must be between {service_obj.min_people} and {service_obj.max_people}'
                    )
            except Service.DoesNotExist:
                raise serializers.ValidationError('Invalid service')
        return value
    
    def validate_service_date(self, value):
        from django.utils import timezone
        if value <= timezone.now():
            raise serializers.ValidationError('Service date must be in the future')
        return value
    
    def create(self, validated_data):
        service = validated_data['service']
        people_count = validated_data['people_count']
        
        base_price = service.calculate_price(people_count)
        
        discount_amount = Decimal('0.00')
        active_discount = service.discounts.filter(is_active=True).first()
        if active_discount and active_discount.is_valid():
            if active_discount.discount_type == 'percentage':
                discount_amount = base_price * (active_discount.discount_value / 100)
            else:
                discount_amount = min(active_discount.discount_value, base_price)
        
        total_price = base_price - discount_amount
        commission_amount = total_price * (service.provider.commission_rate / 100)
        
        customer = self.context['request'].user if self.context['request'].user.is_authenticated else None
        
        order = Order.objects.create(
            customer=customer,
            base_price=base_price,
            discount_amount=discount_amount,
            total_price=total_price,
            commission_amount=commission_amount,
            **validated_data
        )
        
        if active_discount:
            active_discount.used_count += 1
            active_discount.save()
        
        service.bookings_count += 1
        service.save()
        
        return order

class OrderSerializer(serializers.ModelSerializer):
    service = ServiceListSerializer(read_only=True)
    customer = UserSerializer(read_only=True)
    
    class Meta:
        model = Order
        fields = ['id', 'order_number', 'customer', 'service', 'customer_name', 'customer_email',
                 'customer_phone', 'customer_country', 'people_count', 'service_date', 'notes',
                 'base_price', 'discount_amount', 'total_price', 'commission_amount', 'status',
                 'payment_status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'order_number', 'base_price', 'discount_amount', 'total_price',
                           'commission_amount', 'created_at', 'updated_at']