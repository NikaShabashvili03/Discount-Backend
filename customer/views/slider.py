from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from ..serializers.slider import SliderSerializer
from panel.models import Slider
from customer.permissions import AllowAny

class SliderListView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, event_id=None):
        sliders = Slider.objects.all()

        serializer = SliderSerializer(sliders, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)