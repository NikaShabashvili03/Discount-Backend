from rest_framework import serializers
from django.utils import timezone
from services.models import EventReview, EventReviewHelpful, Event


class ReviewerSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    firstname = serializers.CharField(read_only=True)
    lastname = serializers.CharField(read_only=True)
    full_name = serializers.SerializerMethodField()

    def get_full_name(self, obj):
        return f"{getattr(obj, 'firstname', '')} {getattr(obj, 'lastname', '')}".strip()


class EventReviewSerializer(serializers.ModelSerializer):
    """Public-facing review serializer used by customer endpoints."""
    customer = ReviewerSerializer(read_only=True)
    is_owner = serializers.SerializerMethodField()
    is_marked_helpful = serializers.SerializerMethodField()

    class Meta:
        model = EventReview
        fields = [
            'id', 'event', 'customer', 'rating', 'mark', 'title', 'comment',
            'is_approved', 'is_flagged', 'helpful_count', 'is_owner', 'is_marked_helpful',
            'staff_reply', 'staff_reply_at', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'is_approved', 'is_flagged', 'helpful_count', 'staff_reply',
            'staff_reply_at', 'created_at', 'updated_at', 'event',
        ]

    def get_is_owner(self, obj):
        request = self.context.get('request')
        customer = getattr(request, 'customer', None) if request else None
        return bool(customer and customer.is_authenticated and customer.id == obj.customer_id)

    def get_is_marked_helpful(self, obj):
        request = self.context.get('request')
        customer = getattr(request, 'customer', None) if request else None
        if not (customer and customer.is_authenticated):
            return False
        return EventReviewHelpful.objects.filter(review=obj, customer=customer).exists()


class EventReviewCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventReview
        fields = ['rating', 'mark', 'title', 'comment']

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5")
        return value

    def validate_mark(self, value):
        if value and value not in dict(EventReview.MARK_CHOICES):
            raise serializers.ValidationError("Invalid mark")
        return value or 'neutral'


class EventReviewStaffSerializer(serializers.ModelSerializer):
    """Staff/admin facing serializer — exposes moderation fields."""
    customer = ReviewerSerializer(read_only=True)
    event_name = serializers.CharField(source='event.name', read_only=True)

    class Meta:
        model = EventReview
        fields = [
            'id', 'event', 'event_name', 'customer', 'rating', 'mark', 'title', 'comment',
            'is_approved', 'is_flagged', 'flag_reason', 'staff_reply', 'staff_reply_at',
            'helpful_count', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'event', 'customer', 'rating', 'mark', 'title', 'comment',
            'helpful_count', 'staff_reply_at', 'created_at', 'updated_at',
        ]

    def update(self, instance, validated_data):
        if 'staff_reply' in validated_data:
            reply = validated_data['staff_reply']
            instance.staff_reply = reply
            instance.staff_reply_at = timezone.now() if reply else None
        for f in ('is_approved', 'is_flagged', 'flag_reason'):
            if f in validated_data:
                setattr(instance, f, validated_data[f])
        instance.save()
        return instance


class EventRatingSummarySerializer(serializers.Serializer):
    average_rating = serializers.FloatField()
    rating_count = serializers.IntegerField()
    good_count = serializers.IntegerField()
    bad_count = serializers.IntegerField()
    neutral_count = serializers.IntegerField()
    distribution = serializers.DictField(child=serializers.IntegerField())
