from rest_framework import serializers
from services.models import Country

class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = [
            'id', 'name', 'is_active',
            'name_en', 'name_ka', 'name_ru', 'name_hi', 'name_ar', 'name_he'
        ]