from rest_framework import generics, status, permissions, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from ..serializer.city import CitySerializer
from ..models import City


class CityListView(generics.ListAPIView):
    queryset = City.objects.filter(is_active=True)
    serializer_class = CitySerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []