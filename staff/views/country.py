from rest_framework import generics
from rest_framework.decorators import api_view, permission_classes
from ..serializers.country import CountrySerializer
from services.models import Country
from ..permissions import IsStaffAuthenticated
from ..middleware import StaffSessionMiddleware

class CountryListView(generics.ListAPIView):
    queryset = Country.objects.filter(is_active=True)
    serializer_class = CountrySerializer
    permission_classes = [IsStaffAuthenticated]
    authentication_classes = [StaffSessionMiddleware]