from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from services.models import Event
from services.serializers.review import EventRatingSummarySerializer
from ..middleware import CustomerSessionMiddleware
from ..permissions import IsCustomerAuthenticated, AllowAny


# services_eventreview / services_eventreviewhelpful tables are not present on
# prod, so every review endpoint is disabled at the view layer. Read endpoints
# return empty data; write endpoints return 503 so customer-submitted review
# payloads are not silently destroyed.
def _unavailable():
    return Response(
        {'detail': 'Reviews are temporarily unavailable.'},
        status=status.HTTP_503_SERVICE_UNAVAILABLE,
    )


_EMPTY_SUMMARY = {
    'average_rating': 0,
    'rating_count': 0,
    'good_count': 0,
    'bad_count': 0,
    'neutral_count': 0,
    'distribution': {str(i): 0 for i in range(1, 6)},
}


class EventReviewListView(APIView):
    """No reviews to list — table is unavailable."""
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
        return _unavailable()


class EventReviewUpdateDeleteView(APIView):
    permission_classes = [IsCustomerAuthenticated]
    authentication_classes = [CustomerSessionMiddleware]

    def patch(self, request, review_id):
        return _unavailable()

    def put(self, request, review_id):
        return _unavailable()

    def delete(self, request, review_id):
        return _unavailable()


class EventReviewHelpfulToggleView(APIView):
    permission_classes = [IsCustomerAuthenticated]
    authentication_classes = [CustomerSessionMiddleware]

    def post(self, request, review_id):
        return _unavailable()


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
        return _unavailable()
