from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from services.models import Event, Review
from services.serializers.review import ReviewCreateSerializer, ReviewSerializer

from ..middleware import CustomerSessionMiddleware
from ..permissions import AllowAny, IsCustomerAuthenticated


class ReviewListView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, event_id):
        get_object_or_404(Event, id=event_id)
        reviews = Review.objects.filter(event_id=event_id).select_related('customer')
        return Response(ReviewSerializer(reviews, many=True).data)


class ReviewCreateView(APIView):
    permission_classes = [IsCustomerAuthenticated]
    authentication_classes = [CustomerSessionMiddleware]

    def post(self, request, event_id):
        event = get_object_or_404(Event, id=event_id)
        serializer = ReviewCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # One review per (event, customer). Resubmitting overwrites the row
        # instead of creating a duplicate.
        review, created = Review.objects.update_or_create(
            event=event,
            customer=request.customer,
            defaults=serializer.validated_data,
        )
        return Response(
            ReviewSerializer(review).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )
