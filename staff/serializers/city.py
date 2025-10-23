from rest_framework import serializers
from services.models import City
from ..serializers.country import CountrySerializer


class CitySerializer(serializers.ModelSerializer):
    country = CountrySerializer()

    class Meta:
        model = City
        fields = ['id', 'name', 'is_active', 'population', 'country']