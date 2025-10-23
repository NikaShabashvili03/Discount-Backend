from rest_framework import generics, permissions
from django.db.models import Q
from ..serializers.city import CitySerializer
from services.models import City
from ..permissions import IsStaffAuthenticated
from ..middleware import StaffSessionMiddleware

class CityListView(generics.ListAPIView):
    queryset = City.objects.filter(
        Q(is_active=True) & Q(country__is_active=True)
    )
    serializer_class = CitySerializer
    permission_classes = [IsStaffAuthenticated]
    authentication_classes = [StaffSessionMiddleware]