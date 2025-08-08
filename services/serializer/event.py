from rest_framework import serializers
from ..models import Event, Rating, KeyWord

class RatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rating
        fields = ['score']

class KeyWordSerializer(serializers.ModelSerializer):
    class Meta:
        model = KeyWord
        fields = ['word']

class EventSerializer(serializers.ModelSerializer):
    keywords = KeyWordSerializer(many=True, read_only=True)
    rating = RatingSerializer(many=True, read_only=True)
    average_rating = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            'id', 'name', 'location', 'description', 'category',
            'price', 'keywords', 'rating', 'average_rating'
        ]

    def get_average_rating(self, obj):
        ratings = obj.rating.all()
        if ratings.exists():
            return sum(r.score for r in ratings) / ratings.count()
        return None