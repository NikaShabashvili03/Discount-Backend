from rest_framework import serializers
from services.models import City, Country
from .country import CountrySerializer, CountryCreateUpdateSerializer

class CitySerializer(serializers.ModelSerializer):
    country = CountrySerializer()

    class Meta:
        model = City
        fields = ['id', 'name', 'is_active', 'population', 'country']

class CityCreateUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    is_active = serializers.BooleanField(default=True)
    population = serializers.IntegerField(required=False)
    country_id = serializers.IntegerField(write_only=True)

    def validate_country_id(self, country_id):
        try:
            country = Country.objects.get(pk=country_id)
        except Country.DoesNotExist:
            raise serializers.ValidationError("Country not found.")
        return country_id

    def create(self, validated_data):
        country_id = validated_data.pop("country_id")
        country = Country.objects.get(pk=country_id)
        city = City.objects.create(country=country, **validated_data)
        return city

    def update(self, instance, validated_data):
        country_id = validated_data.pop("country_id", None)
        if country_id:
            country = Country.objects.get(pk=country_id)
            instance.country = country
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance