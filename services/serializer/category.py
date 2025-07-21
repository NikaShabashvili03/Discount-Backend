from rest_framework import serializers
from ..models import Category


class CategorySerializer(serializers.ModelSerializer):
    services_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'services_count', 'order', 'icon']
    
    def get_services_count(self, obj):
        return obj.services.filter(is_active=True).count()