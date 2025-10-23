from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from ..serializers.country import CountrySerializer, CountryCreateUpdateSerializer
from services.models import Country
from panel.middleware import AdminSessionMiddleware
from panel.permissions import IsAdminAuthenticated

class CountryAdminListView(generics.ListAPIView):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    permission_classes = [IsAdminAuthenticated]
    authentication_classes = [AdminSessionMiddleware]

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
            return Response({"detail": "Country country_id is required."}, status=status.HTTP_400_BAD_REQUEST)
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
    
class CountryDeleteView(APIView):
    permission_classes = [IsAdminAuthenticated]
    authentication_classes = [AdminSessionMiddleware]

    def delete(self, request, country_id, *args, **kwargs):
        try:
            country = Country.objects.get(pk=country_id)
        except Country.DoesNotExist:
            return Response({"detail": "Country not found."}, status=status.HTTP_404_NOT_FOUND)

        country.delete()
        return Response({"detail": "Country deleted successfully."}, status=status.HTTP_200_OK)