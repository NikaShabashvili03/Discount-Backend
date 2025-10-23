from rest_framework import generics, status, permissions, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q
from ..serializers.city import CitySerializer, CityCreateUpdateSerializer
from services.models import City
from panel.permissions import IsAdminAuthenticated
from panel.middleware import AdminSessionMiddleware

class CityAdminListView(generics.ListAPIView):
    queryset = City.objects.all()
    serializer_class = CitySerializer
    permission_classes = [IsAdminAuthenticated]
    authentication_classes = [AdminSessionMiddleware]

class CityCreateUpdateView(APIView):
    permission_classes = [IsAdminAuthenticated]
    authentication_classes = [AdminSessionMiddleware]

    def post(self, request, *args, **kwargs):
        serializer = CityCreateUpdateSerializer(data=request.data)
        if serializer.is_valid():
            name = serializer.validated_data['name']
            country_id = serializer.validated_data['country_id']

            if City.objects.filter(name__iexact=name, country_id=country_id).exists():
                return Response(
                    {"detail": "City with this name already exists in this country."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            city = serializer.save()
            return Response(CityCreateUpdateSerializer(city).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, *args, **kwargs):
        city_id = request.data.get("city_id")
        if not city_id:
            return Response({"details": "City city_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            city = City.objects.get(pk=city_id)
        except City.DoesNotExist:
            return Response({"detail": "City not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = CityCreateUpdateSerializer(data=request.data, partial=True)
        if serializer.is_valid():
            new_name = serializer.validated_data.get("name")
            new_country_id = serializer.validated_data.get("country_id", city.country_id)

            if new_name and City.objects.filter(
                name__iexact=new_name, country_id=new_country_id
            ).exclude(pk=city_id).exists():
                return Response(
                    {"detail": "Another city with this name already exists in the same country."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            city = serializer.update(city, serializer.validated_data)
            return Response(CityCreateUpdateSerializer(city).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class CityDeleteView(APIView):
    permission_classes = [IsAdminAuthenticated]
    authentication_classes = [AdminSessionMiddleware]

    def delete(self, request, city_id, *args, **kwargs):
        try:
            city = City.objects.get(pk=city_id)
        except City.DoesNotExist:
            return Response({"detail": "City not found."}, status=status.HTTP_404_NOT_FOUND)

        city.delete()
        return Response({"detail": "City deleted successfully."}, status=status.HTTP_200_OK)