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