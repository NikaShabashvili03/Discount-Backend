from rest_framework import serializers
from panel.models import Slider

class SliderUploadSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(required=True)

    class Meta:
        model = Slider
        fields = ['id', 'image', 'title', 'description', 'link']

    def create(self, validated_data):
        admin = self.context['admin']
        return Slider.objects.create(admin=admin, **validated_data)
