from rest_framework import serializers
from services.models import Event
from services.serializers.event import EventListSerializer
from panel.serializers.admin import AdminSerializer
from ..models import Order
from decimal import Decimal

class OrderCreateSerializer(serializers.ModelSerializer):
    # NOTE: customer_name / customer_email / customer_phone / customer_country
    # are intentionally NOT in `fields`. They are populated server-side from the
    # authenticated session customer so a malicious client cannot route the
    # order confirmation email/phone to a third party.
    class Meta:
        model = Order
        fields = ['event', 'people_count', 'event_date', 'notes']

    def validate_event_date(self, value):
        from django.utils import timezone
        if value <= timezone.now():
            raise serializers.ValidationError('Event date must be in the future')
        return value

    def create(self, validated_data):
        event = validated_data['event']
        people_count = validated_data['people_count']
        request = self.context['request']
        customer = request.customer

        # Always source contact info from the authenticated customer, never
        # from request body. Prevents spoofed confirmation emails.
        validated_data['customer_name'] = f"{getattr(customer, 'firstname', '')} {getattr(customer, 'lastname', '')}".strip()
        validated_data['customer_email'] = getattr(customer, 'email', '')
        validated_data['customer_phone'] = getattr(customer, 'mobile', '')
        validated_data['customer_country'] = getattr(customer, 'country', '')

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
                 'created_at', 'updated_at']
        # Every field is read-only on this serializer. Order state transitions
        # (status -> paid/refunded, prices, etc.) MUST come from the BOG callback
        # or admin tooling, never from the customer-facing API. Customer-visible
        # mutable updates need a dedicated, narrowly-scoped serializer.
        read_only_fields = fields