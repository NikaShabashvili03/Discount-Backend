from rest_framework import serializers
from panel.models import Slider

class SliderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Slider
        fields = ['id', 'image', 'title', 'description', 'link']
