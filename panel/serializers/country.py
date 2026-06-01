from rest_framework import serializers
from services.models import Country

class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = [
            'id', 'name', 'is_active',
            'name_en', 'name_ka', 'name_ru', 'name_hi', 'name_ar', 'name_he'
        ]

class CountryCreateUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    name_en = serializers.CharField(max_length=255, required=False, allow_blank=True)
    name_ka = serializers.CharField(max_length=255, required=False, allow_blank=True)
    name_ru = serializers.CharField(max_length=255, required=False, allow_blank=True)
    name_hi = serializers.CharField(max_length=255, required=False, allow_blank=True)
    name_ar = serializers.CharField(max_length=255, required=False, allow_blank=True)
    name_he = serializers.CharField(max_length=255, required=False, allow_blank=True)
    is_active = serializers.BooleanField(default=True)

    def create(self, validated_data):
        country = Country.objects.create(**validated_data)
        return country

    def update(self, instance, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance