from rest_framework import generics, status, permissions, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from ..serializer.country import CountrySerializer, CountryCreateUpdateSerializer
from ..models import Country
from accounts.permissions import AllowAny, IsAdminAuthenticated
from accounts.middleware import AdminSessionMiddleware


class CountryListView(generics.ListAPIView):
    queryset = Country.objects.filter(is_active=True)
    serializer_class = CountrySerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

class CountryCreateUpdateView(APIView):
    permission_classes = [IsAdminAuthenticated]
    authentication_classes = [AdminSessionMiddleware]
    
    def post(self, request, *args, **kwargs):
        serializer = CountryCreateUpdateSerializer(data=request.data)
        if serializer.is_valid():
            name = serializer.validated_data['name']
            if Country.objects.filter(name__iexact=name).exists():
                return Response(
                    {"detail": "Country with this name already exists."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            country = serializer.save()
            return Response(CountryCreateUpdateSerializer(country).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, *args, **kwargs):
        country_id = request.data.get("country_id")
        if not country_id:
            return Response({"id": "Country id is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            country = Country.objects.get(pk=country_id)
        except Country.DoesNotExist:
            return Response({"detail": "Country not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = CountryCreateUpdateSerializer(data=request.data, partial=True)
        if serializer.is_valid():
            new_name = serializer.validated_data.get("name")
            if new_name and Country.objects.filter(name__iexact=new_name).exclude(pk=country_id).exists():
                return Response(
                    {"detail": "Another country with this name already exists."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            country = serializer.update(country, serializer.validated_data)
            return Response(CountryCreateUpdateSerializer(country).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)