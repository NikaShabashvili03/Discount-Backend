from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..middleware import StaffSessionMiddleware
from ..permissions import IsStaffAuthenticated


_EMPTY_SUMMARY = {
    'average_rating': 0,
    'rating_count': 0,
    'good_count': 0,
    'bad_count': 0,
    'neutral_count': 0,
    'distribution': {str(i): 0 for i in range(1, 6)},
}


def _fake_staff_review(review_id, **overrides):
    now = timezone.now().isoformat()
    payload = {
        'id': review_id,
        'event': 0,
        'event_name': '',
        'customer': {'id': None, 'firstname': '', 'lastname': '', 'full_name': ''},
        'rating': 0,
        'comment': '',
        'created_at': now,
    }
    payload.update(overrides)
    return payload


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
        return Response(_EMPTY_SUMMARY)


class ReviewModerationView(APIView):
    permission_classes = [IsStaffAuthenticated]
    authentication_classes = [StaffSessionMiddleware]

    def get(self, request, review_id):
        return Response(_fake_staff_review(review_id))

    def patch(self, request, review_id):
        return Response(_fake_staff_review(review_id))

    def delete(self, request, review_id):
        return Response({'detail': 'Review deleted'}, status=status.HTTP_200_OK)


class ReviewApproveView(APIView):
    permission_classes = [IsStaffAuthenticated]
    authentication_classes = [StaffSessionMiddleware]

    def post(self, request, review_id):
        return Response(_fake_staff_review(review_id))


class ReviewHideView(APIView):
    permission_classes = [IsStaffAuthenticated]
    authentication_classes = [StaffSessionMiddleware]

    def post(self, request, review_id):
        return Response(_fake_staff_review(review_id))


class ReviewReplyView(APIView):
    permission_classes = [IsStaffAuthenticated]
    authentication_classes = [StaffSessionMiddleware]

    def post(self, request, review_id):
        return Response(_fake_staff_review(review_id))
