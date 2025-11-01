from rest_framework import serializers
from services.models import Category

class CategorySerializer(serializers.ModelSerializer):
    events_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'activity', 'color', 'description', 'events_count', 'order', 'icon']
    
    def get_events_count(self, obj):
        return obj.events.filter(is_active=True).count()