from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from ..serializers.slider import SliderUploadSerializer
from panel.permissions import IsAdminAuthenticated
from panel.middleware import AdminSessionMiddleware
from panel.models import Slider

class SliderUploadView(APIView):
    permission_classes = [IsAdminAuthenticated]
    authentication_classes = [AdminSessionMiddleware]

    def post(self, request):
        admin = getattr(request, 'admin', None) 

        if not admin:
            return Response(
                {"detail": "Admin authentication required."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        serializer = SliderUploadSerializer(
            data=request.data, context={'admin': admin}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SliderDeleteView(APIView):
    permission_classes = [IsAdminAuthenticated]
    authentication_classes = [AdminSessionMiddleware]

    def delete(self, request, id):
        try:
            slider = Slider.objects.get(id=id)
        except Slider.DoesNotExist:
            return Response(
                {"detail": "Slider not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        slider.delete()
        return Response(
            {"detail": "Slider deleted successfully."}
        )