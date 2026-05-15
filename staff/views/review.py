from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from services.serializers.review import EventRatingSummarySerializer
from ..permissions import IsStaffAuthenticated
from ..middleware import StaffSessionMiddleware


# services_eventreview table is not present on prod, so every staff review
# endpoint is disabled at the view layer. Read endpoints return empty data
# (the staff dashboard renders cleanly); write endpoints return 503 so
# moderator actions are not silently swallowed.
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


class CompanyReviewListView(APIView):
    permission_classes = [IsStaffAuthenticated]
    authentication_classes = [StaffSessionMiddleware]

    def get(self, request, company_id):
        return Response([])


class EventReviewListForStaffView(APIView):
    permission_classes = [IsStaffAuthenticated]
    authentication_classes = [StaffSessionMiddleware]

    def get(self, request, event_id):
        return Response([])


class EventReviewSummaryForStaffView(APIView):
    permission_classes = [IsStaffAuthenticated]
    authentication_classes = [StaffSessionMiddleware]

    def get(self, request, event_id):
        return Response(EventRatingSummarySerializer(_EMPTY_SUMMARY).data)


class ReviewModerationView(APIView):
    permission_classes = [IsStaffAuthenticated]
    authentication_classes = [StaffSessionMiddleware]

    def get(self, request, review_id):
        return _unavailable()

    def patch(self, request, review_id):
        return _unavailable()

    def delete(self, request, review_id):
        return _unavailable()


class ReviewApproveView(APIView):
    permission_classes = [IsStaffAuthenticated]
    authentication_classes = [StaffSessionMiddleware]

    def post(self, request, review_id):
        return _unavailable()


class ReviewHideView(APIView):
    permission_classes = [IsStaffAuthenticated]
    authentication_classes = [StaffSessionMiddleware]

    def post(self, request, review_id):
        return _unavailable()


class ReviewReplyView(APIView):
    permission_classes = [IsStaffAuthenticated]
    authentication_classes = [StaffSessionMiddleware]

    def post(self, request, review_id):
        return _unavailable()
