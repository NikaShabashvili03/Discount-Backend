from rest_framework import serializers
from services.models import Event, EventImage, Discount, CompanyCategory
from .category import CategorySerializer
from .city import CitySerializer
from decimal import Decimal

class EventImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventImage
        fields = ['id', 'alt_text', 'image', 'is_primary', 'order']

class DiscountSerializer(serializers.ModelSerializer):
    is_valid = serializers.SerializerMethodField()
    
    class Meta:
        model = Discount
        fields = ['id', 'name', 'discount_type', 'discount_value', 
                 'start_date', 'end_date', 'is_active', 'is_valid', 'max_uses', 'used_count']
    
    def get_is_valid(self, obj):
        return obj.is_valid()

class EventListSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    city = CitySerializer(read_only=True)
    primary_image = serializers.SerializerMethodField()
    current_discount = serializers.SerializerMethodField()
    discounted_price = serializers.SerializerMethodField()
    
    class Meta:
        model = Event
        fields = ['id', 'name', 'description',
                 'base_price', 'price_per_person', 'min_people', 'max_people', 'location',
                 'is_popular', 'is_featured', 'views_count', 'bookings_count', 'category', 'city',
                 'company', 'primary_image', 'longitude', 'latitude', 'current_discount', 'discounted_price', 'created_at']
    
    def get_primary_image(self, obj):
        primary_image = obj.images.filter(is_primary=True).first()
        if primary_image:
            return EventImageSerializer(primary_image).data
        return None
    
    def get_current_discount(self, obj):
        active_discount = obj.discounts.filter(is_active=True).first()
        if active_discount and active_discount.is_valid():
            return DiscountSerializer(active_discount).data
        return None
    
    def get_discounted_price(self, obj):
        discount = self.get_current_discount(obj)
        if discount:
            discount_obj = obj.discounts.filter(is_active=True).first()
            if discount_obj.discount_type == 'percentage':
                return obj.base_price * (1 - discount_obj.discount_value / 100)
            else:
                return max(obj.base_price - discount_obj.discount_value, 0)
        return obj.base_price
    
class EventDetailSerializer(EventListSerializer):
    images = EventImageSerializer(many=True, read_only=True)
    discounts = DiscountSerializer(many=True, read_only=True)
    
    class Meta(EventListSerializer.Meta):
        fields = EventListSerializer.Meta.fields + ['images', 'discounts']
    
class ProviderStatsSerializer(serializers.Serializer):
    total_events = serializers.IntegerField()
    total_orders = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    commission_owed = serializers.DecimalField(max_digits=10, decimal_places=2)
    active_orders = serializers.IntegerField()
    completed_orders = serializers.IntegerField()
    popular_events = serializers.ListField()

class EventStatsSerializer(serializers.Serializer):
    event_id = serializers.UUIDField()
    event_name = serializers.CharField()
    total_bookings = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    average_rating = serializers.DecimalField(max_digits=3, decimal_places=2, allow_null=True)
    views_count = serializers.IntegerField()


class PriceCalculationSerializer(serializers.Serializer):
    event_id = serializers.UUIDField()
    people_count = serializers.IntegerField(min_value=1)
    
    def validate(self, attrs):
        try:
            event = Event.objects.get(
                id=attrs['event_id'], 
                is_active=True,
                city__is_active=True,
                city__country__is_active=True,
                category__is_active=True
            )
            attrs['event'] = event
        except Event.DoesNotExist:
            raise serializers.ValidationError('Event not found')
        
        people_count = attrs['people_count']
        if people_count < event.min_people or people_count > event.max_people:
            raise serializers.ValidationError(
                f'People count must be between {event.min_people} and {event.max_people}'
            )
        
        return attrs
    
    def to_representation(self, instance):
        event = instance['event']
        people_count = instance['people_count']
        
        base_price = event.calculate_price(people_count)
        discount_amount = Decimal('0.00')
        discount_info = None
        
        # Check for active discount
        active_discount = event.discounts.filter(is_active=True).first()
        if active_discount and active_discount.is_valid():
            if active_discount.discount_type == 'percentage':
                discount_amount = base_price * (active_discount.discount_value / 100)
            else:
                discount_amount = min(active_discount.discount_value, base_price)
            
            discount_info = {
                'name': active_discount.name,
                'type': active_discount.discount_type,
                'value': active_discount.discount_value,
                'amount': discount_amount
            }
        
        total_price = base_price - discount_amount
        
        return {
            'event_id': event.id,
            'event_name': event.name,
            'people_count': people_count,
            'base_price': base_price,
            'discount': discount_info,
            'discount_amount': discount_amount,
            'total_price': total_price
        }