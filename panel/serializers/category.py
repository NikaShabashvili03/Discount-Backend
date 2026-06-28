from rest_framework import serializers
from services.models import Category


class CategorySerializer(serializers.ModelSerializer):
    events_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = [
            'id', 'name', 'activity', 'color', 'description', 'events_count', 'order', 'icon',
            'name_en', 'name_ka', 'name_ru', 'name_hi', 'name_ar', 'name_he',
            'description_en', 'description_ka', 'description_ru', 'description_hi', 'description_ar', 'description_he'
        ]
    
    def get_events_count(self, obj):
        return obj.events.filter(is_active=True).count()
    

class CategoryCreateUpdateSerializer(serializers.Serializer):
    ACTIVITY_CHOICE = (
        ('water', 'Water activity'),
        ('land', 'Land activity')
    )
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    
    name_en = serializers.CharField(max_length=255, required=False, allow_blank=True)
    name_ka = serializers.CharField(max_length=255, required=False, allow_blank=True)
    name_ru = serializers.CharField(max_length=255, required=False, allow_blank=True)
    name_hi = serializers.CharField(max_length=255, required=False, allow_blank=True)
    name_ar = serializers.CharField(max_length=255, required=False, allow_blank=True)
    name_he = serializers.CharField(max_length=255, required=False, allow_blank=True)

    description_en = serializers.CharField(required=False, allow_blank=True)
    description_ka = serializers.CharField(required=False, allow_blank=True)
    description_ru = serializers.CharField(required=False, allow_blank=True)
    description_hi = serializers.CharField(required=False, allow_blank=True)
    description_ar = serializers.CharField(required=False, allow_blank=True)
    description_he = serializers.CharField(required=False, allow_blank=True)
    order = serializers.IntegerField(required=False)
    color = serializers.CharField(required=False)
    icon = serializers.CharField(required=False, allow_blank=True)
    is_active = serializers.BooleanField(default=True)
    category_id = serializers.IntegerField(required=False, write_only=True)
    activity = serializers.ChoiceField(choices=ACTIVITY_CHOICE)

    def create(self, validated_data):
        validated_data.pop("category_id", None)
        return Category.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data.pop("category_id", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance