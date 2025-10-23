from django.db.models import Q
from rest_framework import generics, permissions
from services.serializers.city import CitySerializer
from services.models import City

class CityListView(generics.ListAPIView):
    queryset = City.objects.filter(
        Q(is_active=True) & Q(country__is_active=True)
    )
    serializer_class = CitySerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []