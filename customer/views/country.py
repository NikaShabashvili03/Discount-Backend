from rest_framework import generics, permissions
from services.serializers.country import CountrySerializer
from services.models import Country

class CountryListView(generics.ListAPIView):
    queryset = Country.objects.filter(is_active=True)
    serializer_class = CountrySerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []