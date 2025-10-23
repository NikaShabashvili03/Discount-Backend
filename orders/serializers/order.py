from rest_framework import serializers
from services.models import Event
from services.serializers.event import EventListSerializer
from panel.serializers.admin import AdminSerializer
from ..models import Order
from decimal import Decimal

class OrderCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['event', 'customer_name', 'customer_email', 'customer_phone', 'customer_country',
                 'people_count', 'event_date', 'notes']
    
    def validate_people_count(self, value):
        event = self.initial_data.get('event')
        if event:
            try:
                event_obj = Event.objects.get(id=event)
                if value < event_obj.min_people or value > event_obj.max_people:
                    raise serializers.ValidationError(
                        f'People count must be between {event_obj.min_people} and {event_obj.max_people}'
                    )
            except Event.DoesNotExist:
                raise serializers.ValidationError('Invalid event')
        return value
    
    def validate_event_date(self, value):
        from django.utils import timezone
        if value <= timezone.now():
            raise serializers.ValidationError('Event date must be in the future')
        return value
    
    def create(self, validated_data):
        event = validated_data['event']
        people_count = validated_data['people_count']
        
        base_price = event.calculate_price(people_count)
        
        discount_amount = Decimal('0.00')
        active_discount = event.discounts.filter(is_active=True).first()
        if active_discount and active_discount.is_valid():
            if active_discount.discount_type == 'percentage':
                discount_amount = base_price * (active_discount.discount_value / 100)
            else:
                discount_amount = min(active_discount.discount_value, base_price)
        
        total_price = base_price - discount_amount
        commission_amount = total_price * (event.company.commission_rate / 100)
        
        customer = self.context['request'].customer if self.context['request'].customer.is_authenticated else None
        
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
        
        event.bookings_count += 1
        event.save()
        
        return order

class OrderSerializer(serializers.ModelSerializer):
    event = EventListSerializer(read_only=True)
    customer = AdminSerializer(read_only=True)
    
    class Meta:
        model = Order
        fields = ['id', 'order_number', 'customer', 'event', 'customer_name', 'customer_email',
                 'customer_phone', 'customer_country', 'people_count', 'event_date', 'notes',
                 'base_price', 'discount_amount', 'total_price', 'commission_amount', 'status',
                 'payment_status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'order_number', 'base_price', 'discount_amount', 'total_price',
                           'commission_amount', 'created_at', 'updated_at']