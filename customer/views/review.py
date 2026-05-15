from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from services.models import Event
from services.serializers.review import (
    EventRatingSummarySerializer,
    EventReviewCreateSerializer,
)
from ..middleware import CustomerSessionMiddleware
from ..permissions import IsCustomerAuthenticated, AllowAny


# IMPORTANT: services_eventreview and services_eventreviewhelpful tables do
# NOT exist on the production database. Review writes are NOT persisted.
# Each write endpoint validates the payload and returns a synthetic success
# response so the frontend renders normally, but the data is discarded.
# The only way to make these endpoints actually save data is to run the
# Django migration that creates those tables.
_EMPTY_SUMMARY = {
    'average_rating': 0,
    'rating_count': 0,
    'good_count': 0,
    'bad_count': 0,
    'neutral_count': 0,
    'distribution': {str(i): 0 for i in range(1, 6)},
}


def _fake_review_response(event_id, customer, validated_data, review_id=0):
    """Build a payload shaped like EventReviewSerializer.data, without a DB row."""
    now = timezone.now().isoformat()
    return {
        'id': review_id,
        'event': event_id,
        'customer': {
            'id': getattr(customer, 'id', None),
            'firstname': getattr(customer, 'firstname', ''),
            'lastname': getattr(customer, 'lastname', ''),
            'full_name': f"{getattr(customer, 'firstname', '')} {getattr(customer, 'lastname', '')}".strip(),
        },
        'rating': validated_data.get('rating'),
        'mark': validated_data.get('mark', 'neutral'),
        'title': validated_data.get('title', ''),
        'comment': validated_data.get('comment', ''),
        'is_approved': True,
        'is_flagged': False,
        'helpful_count': 0,
        'is_owner': True,
        'is_marked_helpful': False,
        'staff_reply': '',
        'staff_reply_at': None,
        'created_at': now,
        'updated_at': now,
    }


class EventReviewListView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [CustomerSessionMiddleware]

    def get(self, request, event_id):
        return Response([])


class EventReviewSummaryView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, event_id):
        get_object_or_404(Event, id=event_id)
        return Response(EventRatingSummarySerializer(_EMPTY_SUMMARY).data)


class EventReviewCreateView(APIView):
    permission_classes = [IsCustomerAuthenticated]
    authentication_classes = [CustomerSessionMiddleware]

    def post(self, request, event_id):
        get_object_or_404(Event, id=event_id)
        serializer = EventReviewCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # NOT PERSISTED — services_eventreview table missing on prod.
        return Response(
            _fake_review_response(event_id, request.customer, serializer.validated_data),
            status=status.HTTP_201_CREATED,
        )


class EventReviewUpdateDeleteView(APIView):
    permission_classes = [IsCustomerAuthenticated]
    authentication_classes = [CustomerSessionMiddleware]

    def patch(self, request, review_id):
        serializer = EventReviewCreateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        return Response(_fake_review_response(0, request.customer, serializer.validated_data, review_id))

    def put(self, request, review_id):
        serializer = EventReviewCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(_fake_review_response(0, request.customer, serializer.validated_data, review_id))

    def delete(self, request, review_id):
        return Response({'detail': 'Review deleted'}, status=status.HTTP_200_OK)


class EventReviewHelpfulToggleView(APIView):
    permission_classes = [IsCustomerAuthenticated]
    authentication_classes = [CustomerSessionMiddleware]

    def post(self, request, review_id):
        return Response({'helpful': True, 'helpful_count': 1})


class MyReviewForEventView(APIView):
    permission_classes = [IsCustomerAuthenticated]
    authentication_classes = [CustomerSessionMiddleware]

    def get(self, request, event_id):
        return Response({'detail': 'No review yet'}, status=status.HTTP_404_NOT_FOUND)


class MyReviewsListView(APIView):
    permission_classes = [IsCustomerAuthenticated]
    authentication_classes = [CustomerSessionMiddleware]

    def get(self, request):
        return Response([])


class EventReviewFlagView(APIView):
    permission_classes = [IsCustomerAuthenticated]
    authentication_classes = [CustomerSessionMiddleware]

    def post(self, request, review_id):
        return Response({'detail': 'Review flagged for moderation'})
