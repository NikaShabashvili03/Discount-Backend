from rest_framework import serializers

from services.models import Review


class ReviewSerializer(serializers.ModelSerializer):
    customer_name = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ['id', 'event', 'customer', 'customer_name', 'rating', 'comment', 'created_at']
        read_only_fields = ['id', 'event', 'customer', 'customer_name', 'created_at']

    def get_customer_name(self, obj):
        return f"{obj.customer.firstname} {obj.customer.lastname}".strip()


class ReviewCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
