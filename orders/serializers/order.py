from rest_framework import serializers
from services.models import Event, EventAgePrice
from services.serializers.event import EventListSerializer
from panel.serializers.admin import AdminSerializer
from ..models import Order, OrderAgePrice
from decimal import Decimal

class OrderAgePriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderAgePrice
        fields = ['id', 'category_name', 'min_age', 'max_age', 'price', 'quantity']

class OrderAgePriceCreateSerializer(serializers.Serializer):
    age_price_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)

class OrderCreateSerializer(serializers.ModelSerializer):
    # NOTE: customer_name / customer_email / customer_phone / customer_country
    # are intentionally NOT in `fields`. They are populated server-side from the
    # authenticated session customer so a malicious client cannot route the
    # order confirmation email/phone to a third party.
    adults_count = serializers.IntegerField(required=False, default=0, min_value=0)
    children_count = serializers.IntegerField(required=False, default=0, min_value=0)
    infants_count = serializers.IntegerField(required=False, default=0, min_value=0)
    people_count = serializers.IntegerField(required=False, min_value=1)
    age_prices = OrderAgePriceCreateSerializer(many=True, required=False)

    class Meta:
        model = Order
        fields = ['event', 'people_count', 'event_date', 'notes', 'adults_count', 'children_count', 'infants_count', 'age_prices']

    def validate_event_date(self, value):
        from django.utils import timezone
        if value <= timezone.now():
            raise serializers.ValidationError('Event date must be in the future')
        return value

    def create(self, validated_data):
        event = validated_data['event']
        age_prices_data = validated_data.pop('age_prices', None)

        if age_prices_data:
            people_count = 0
            adults_count = 0
            children_count = 0
            infants_count = 0
            
            for item in age_prices_data:
                try:
                    ap = event.age_prices.get(id=item['age_price_id'])
                except EventAgePrice.DoesNotExist:
                    raise serializers.ValidationError({"age_prices": f"Age price category with ID {item['age_price_id']} not found."})
                
                qty = item['quantity']
                people_count += qty
                if ap.max_age <= 2:
                    infants_count += qty
                elif ap.max_age <= 12:
                    children_count += qty
                else:
                    adults_count += qty
            
        event_date = validated_data.get('event_date')
        if age_prices_data:
            people_count = 0
            adults_count = 0
            children_count = 0
            infants_count = 0
            
            for item in age_prices_data:
                try:
                    ap = event.age_prices.get(id=item['age_price_id'])
                except EventAgePrice.DoesNotExist:
                    raise serializers.ValidationError({"age_prices": f"Age price category with ID {item['age_price_id']} not found."})
                
                qty = item['quantity']
                people_count += qty
                if ap.max_age <= 2:
                    infants_count += qty
                elif ap.max_age <= 12:
                    children_count += qty
                else:
                    adults_count += qty
            
            base_price = event.calculate_price(age_prices_data=age_prices_data, event_date=event_date)
        else:
            people_count = validated_data.get('people_count')
            adults_count = validated_data.get('adults_count', 0)
            children_count = validated_data.get('children_count', 0)
            infants_count = validated_data.get('infants_count', 0)

            # If age counts are not provided but people_count is, default adults_count to people_count
            if adults_count == 0 and children_count == 0 and infants_count == 0:
                if not people_count:
                    people_count = 1
                adults_count = people_count
            else:
                people_count = adults_count + children_count + infants_count
            
            base_price = event.calculate_price(people_count, adults_count, children_count, infants_count, event_date=event_date)

        validated_data['people_count'] = people_count
        validated_data['adults_count'] = adults_count
        validated_data['children_count'] = children_count
        validated_data['infants_count'] = infants_count

        request = self.context['request']
        customer = request.customer

        # Always source contact info from the authenticated customer, never
        # from request body. Prevents spoofed confirmation emails.
        validated_data['customer_name'] = f"{getattr(customer, 'firstname', '')} {getattr(customer, 'lastname', '')}".strip()
        validated_data['customer_email'] = getattr(customer, 'email', '')
        validated_data['customer_phone'] = getattr(customer, 'mobile', '')
        validated_data['customer_country'] = getattr(customer, 'country', '')
        validated_data['event_ticket'] = event.event_ticket

        discount_amount = Decimal('0.00')
        active_discount = event.discounts.filter(is_active=True).first()
        if active_discount and active_discount.is_valid():
            if active_discount.discount_type == 'percentage':
                discount_amount = base_price * (active_discount.discount_value / 100)
            else:
                discount_amount = min(active_discount.discount_value, base_price)

        total_price = base_price - discount_amount
        commission_amount = total_price * (event.company.commission_rate / 100)

        order = Order.objects.create(
            customer=customer,
            base_price=base_price,
            discount_amount=discount_amount,
            total_price=total_price,
            commission_amount=commission_amount,
            **validated_data
        )

        if age_prices_data:
            for item in age_prices_data:
                ap = event.age_prices.get(id=item['age_price_id'])
                OrderAgePrice.objects.create(
                    order=order,
                    category_name=ap.category_name,
                    min_age=ap.min_age,
                    max_age=ap.max_age,
                    price=ap.price,
                    quantity=item['quantity'],
                    start_time=ap.start_time,
                    end_time=ap.end_time
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
    age_prices = OrderAgePriceSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'order_number', 'customer', 'event', 'customer_name', 'customer_email',
                 'customer_phone', 'customer_country', 'people_count', 'adults_count', 'children_count',
                 'infants_count', 'event_date', 'notes',
                 'base_price', 'discount_amount', 'total_price', 'commission_amount', 'status',
                 'event_ticket', 'is_used', 'created_at', 'updated_at', 'age_prices']
        # Every field is read-only on this serializer. Order state transitions
        # (status -> paid/refunded, prices, etc.) MUST come from the BOG callback
        # or admin tooling, never from the customer-facing API. Customer-visible
        # mutable updates need a dedicated, narrowly-scoped serializer.
        read_only_fields = fields