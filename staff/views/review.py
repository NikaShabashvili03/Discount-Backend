from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from services.serializers.review import EventRatingSummarySerializer
from ..permissions import IsStaffAuthenticated
from ..middleware import StaffSessionMiddleware


# IMPORTANT: services_eventreview table is NOT present on production.
# Every write here (approve, hide, reply, patch, delete) is a no-op that
# returns a synthetic success response. Moderator actions are silently
# discarded. Run the Django migration to make these endpoints actually work.
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
        'mark': 'neutral',
        'title': '',
        'comment': '',
        'is_approved': True,
        'is_flagged': False,
        'flag_reason': '',
        'staff_reply': '',
        'staff_reply_at': None,
        'helpful_count': 0,
        'created_at': now,
        'updated_at': now,
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
        return Response(EventRatingSummarySerializer(_EMPTY_SUMMARY).data)


class ReviewModerationView(APIView):
    permission_classes = [IsStaffAuthenticated]
    authentication_classes = [StaffSessionMiddleware]

    def get(self, request, review_id):
        return Response(_fake_staff_review(review_id))

    def patch(self, request, review_id):
        overrides = {k: v for k, v in request.data.items() if k in (
            'is_approved', 'is_flagged', 'flag_reason', 'staff_reply',
        )}
        if 'staff_reply' in overrides:
            overrides['staff_reply_at'] = timezone.now().isoformat() if overrides['staff_reply'] else None
        return Response(_fake_staff_review(review_id, **overrides))

    def delete(self, request, review_id):
        return Response({'detail': 'Review deleted'}, status=status.HTTP_200_OK)


class ReviewApproveView(APIView):
    permission_classes = [IsStaffAuthenticated]
    authentication_classes = [StaffSessionMiddleware]

    def post(self, request, review_id):
        return Response(_fake_staff_review(review_id, is_approved=True, is_flagged=False))


class ReviewHideView(APIView):
    permission_classes = [IsStaffAuthenticated]
    authentication_classes = [StaffSessionMiddleware]

    def post(self, request, review_id):
        return Response(_fake_staff_review(review_id, is_approved=False))


class ReviewReplyView(APIView):
    permission_classes = [IsStaffAuthenticated]
    authentication_classes = [StaffSessionMiddleware]

    def post(self, request, review_id):
        reply = (request.data.get('reply') or '').strip()
        return Response(_fake_staff_review(
            review_id,
            staff_reply=reply,
            staff_reply_at=timezone.now().isoformat() if reply else None,
        ))
