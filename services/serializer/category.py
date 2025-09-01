from rest_framework import serializers
from ..models import Category


class CategorySerializer(serializers.ModelSerializer):
    events_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'color', 'description', 'events_count', 'order', 'icon']
    
    def get_events_count(self, obj):
        return obj.events.filter(is_active=True).count()
    

class CategoryCreateUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    order = serializers.IntegerField(required=False)
    color = serializers.CharField(required=False)
    icon = serializers.CharField(required=False, allow_blank=True)
    is_active = serializers.BooleanField(default=True)
    category_id = serializers.IntegerField(required=False, write_only=True)

    def create(self, validated_data):
        validated_data.pop("category_id", None)
        return Category.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data.pop("category_id", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance