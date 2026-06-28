from rest_framework import serializers
from services.models import Event, EventImage, EventVideo, Discount, CompanyCategory, EventAgePrice
from .category import CategorySerializer
from .city import CitySerializer
from decimal import Decimal

class EventImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventImage
        fields = ['id', 'alt_text', 'image', 'is_primary', 'order']

class EventVideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventVideo
        fields = ['id', 'alt_text', 'video', 'is_primary', 'order']

class EventAgePriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventAgePrice
        fields = ['id', 'category_name', 'min_age', 'max_age', 'price', 'start_time', 'end_time']

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
    average_rating = serializers.SerializerMethodField()
    rating_count = serializers.SerializerMethodField()
    good_reviews_count = serializers.SerializerMethodField()
    bad_reviews_count = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            'id', 'name', 'description',
            'base_price', 'price_per_person', 'adult_price', 'child_price', 'infant_price',
            'min_people', 'max_people', 'location',
            'is_popular', 'is_featured', 'views_count', 'bookings_count', 'category', 'city',
            'company', 'primary_image', 'longitude', 'latitude', 'current_discount', 'discounted_price',
            'average_rating', 'rating_count', 'good_reviews_count', 'bad_reviews_count', 'created_at',
            'event_ticket',
            'name_en', 'name_ka', 'name_ru', 'name_hi', 'name_ar', 'name_he',
            'description_en', 'description_ka', 'description_ru', 'description_hi', 'description_ar', 'description_he'
        ]
    
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

    def get_average_rating(self, obj):
        avg = getattr(obj, 'avg_rating', None)
        return round(avg, 2) if avg is not None else 0

    def get_rating_count(self, obj):
        return getattr(obj, 'review_count', 0) or 0

    def get_good_reviews_count(self, obj):
        return getattr(obj, 'good_count', 0) or 0

    def get_bad_reviews_count(self, obj):
        return getattr(obj, 'bad_count', 0) or 0

class EventDetailSerializer(EventListSerializer):
    images = EventImageSerializer(many=True, read_only=True)
    videos = serializers.SerializerMethodField()
    discounts = DiscountSerializer(many=True, read_only=True)
    age_prices = EventAgePriceSerializer(many=True, read_only=True)

    class Meta(EventListSerializer.Meta):
        fields = EventListSerializer.Meta.fields + ['images', 'videos', 'discounts', 'age_prices']

    def get_videos(self, obj):
        # services_eventvideo table is not present on prod; skip the JOIN.
        return []
    
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
    people_count = serializers.IntegerField(required=False, min_value=1)
    adults_count = serializers.IntegerField(required=False, min_value=0, default=0)
    children_count = serializers.IntegerField(required=False, min_value=0, default=0)
    infants_count = serializers.IntegerField(required=False, min_value=0, default=0)
    event_date = serializers.DateTimeField(required=False, allow_null=True)
    age_prices = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        allow_empty=True
    )
    
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
        
        return attrs
    
    def to_representation(self, instance):
        event = instance['event']
        age_prices_data = instance.get('age_prices')
        event_date = instance.get('event_date')
        
        if age_prices_data:
            people_count = 0
            adults_count = 0
            children_count = 0
            infants_count = 0
            for item in age_prices_data:
                try:
                    ap = event.age_prices.get(id=item.get('age_price_id'))
                    qty = item.get('quantity', 0)
                    people_count += qty
                    if ap.max_age <= 2:
                        infants_count += qty
                    elif ap.max_age <= 12:
                        children_count += qty
                    else:
                        adults_count += qty
                except EventAgePrice.DoesNotExist:
                    pass
            base_price = event.calculate_price(age_prices_data=age_prices_data, event_date=event_date)
        else:
            adults_count = instance.get('adults_count', 0)
            children_count = instance.get('children_count', 0)
            infants_count = instance.get('infants_count', 0)
            
            if adults_count == 0 and children_count == 0 and infants_count == 0:
                people_count = instance.get('people_count', 1)
                adults_count = people_count
            else:
                people_count = adults_count + children_count + infants_count
                
            base_price = event.calculate_price(people_count, adults_count, children_count, infants_count, event_date=event_date)
            
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
            'adults_count': adults_count,
            'children_count': children_count,
            'infants_count': infants_count,
            'base_price': base_price,
            'discount': discount_info,
            'discount_amount': discount_amount,
            'total_price': total_price
        }