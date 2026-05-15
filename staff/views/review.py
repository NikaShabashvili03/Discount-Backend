from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from services.models import Event, EventReview
from services.serializers.review import (
    EventReviewStaffSerializer,
    EventRatingSummarySerializer,
)
from ..models.staff import CompanyStaff
from ..permissions import IsStaffAuthenticated
from ..middleware import StaffSessionMiddleware


def _staff_company_ids(staff):
    return CompanyStaff.objects.filter(staff=staff).values_list('company_id', flat=True)


def _ensure_event_belongs_to_staff(staff, event_id):
    event = get_object_or_404(Event, id=event_id)
    if event.company_id not in list(_staff_company_ids(staff)):
        return None
    return event


class CompanyReviewListView(APIView):
    """List all reviews for events owned by the staff's company."""
    permission_classes = [IsStaffAuthenticated]
    authentication_classes = [StaffSessionMiddleware]

    def get(self, request, company_id):
        if not CompanyStaff.objects.filter(staff=request.staff, company_id=company_id).exists():
            return Response({'detail': 'You do not belong to this company'}, status=403)

        mark = request.query_params.get('mark')
        flagged = request.query_params.get('flagged')
        approved = request.query_params.get('approved')
        event_id = request.query_params.get('event')

        qs = EventReview.objects.filter(event__company_id=company_id).select_related('customer', 'event')
        if mark in dict(EventReview.MARK_CHOICES):
            qs = qs.filter(mark=mark)
        if flagged in ('1', 'true', 'True'):
            qs = qs.filter(is_flagged=True)
        if approved in ('0', 'false', 'False'):
            qs = qs.filter(is_approved=False)
        elif approved in ('1', 'true', 'True'):
            qs = qs.filter(is_approved=True)
        if event_id:
            qs = qs.filter(event_id=event_id)

        serializer = EventReviewStaffSerializer(qs.order_by('-created_at'), many=True)
        return Response(serializer.data)


class EventReviewListForStaffView(APIView):
    """All reviews for one event (staff must belong to event.company)."""
    permission_classes = [IsStaffAuthenticated]
    authentication_classes = [StaffSessionMiddleware]

    def get(self, request, event_id):
        event = _ensure_event_belongs_to_staff(request.staff, event_id)
        if event is None:
            return Response({'detail': 'You do not belong to this company'}, status=403)
        reviews = EventReview.objects.filter(event=event).select_related('customer').order_by('-created_at')
        return Response(EventReviewStaffSerializer(reviews, many=True).data)


class EventReviewSummaryForStaffView(APIView):
    """Aggregate rating data for a single event."""
    permission_classes = [IsStaffAuthenticated]
    authentication_classes = [StaffSessionMiddleware]

    def get(self, request, event_id):
        event = _ensure_event_belongs_to_staff(request.staff, event_id)
        if event is None:
            return Response({'detail': 'You do not belong to this company'}, status=403)

        qs = EventReview.objects.filter(event=event)
        agg = qs.aggregate(avg=Avg('rating'), count=Count('id'))
        marks = qs.aggregate(
            good=Count('id', filter=Q(mark='good')),
            bad=Count('id', filter=Q(mark='bad')),
            neutral=Count('id', filter=Q(mark='neutral')),
        )
        distribution = {str(i): 0 for i in range(1, 6)}
        for row in qs.values('rating').annotate(c=Count('id')):
            distribution[str(row['rating'])] = row['c']
        data = {
            'average_rating': round(agg['avg'] or 0, 2),
            'rating_count': agg['count'] or 0,
            'good_count': marks['good'] or 0,
            'bad_count': marks['bad'] or 0,
            'neutral_count': marks['neutral'] or 0,
            'distribution': distribution,
        }
        return Response(EventRatingSummarySerializer(data).data)


class ReviewModerationView(APIView):
    """Single-review moderation: reply, approve/hide, flag/unflag, delete."""
    permission_classes = [IsStaffAuthenticated]
    authentication_classes = [StaffSessionMiddleware]

    def _get_owned_review(self, request, review_id):
        review = get_object_or_404(EventReview, id=review_id)
        if review.event.company_id not in list(_staff_company_ids(request.staff)):
            return None
        return review

    def get(self, request, review_id):
        review = self._get_owned_review(request, review_id)
        if review is None:
            return Response({'detail': 'Not allowed'}, status=403)
        return Response(EventReviewStaffSerializer(review).data)

    def patch(self, request, review_id):
        review = self._get_owned_review(request, review_id)
        if review is None:
            return Response({'detail': 'Not allowed'}, status=403)
        serializer = EventReviewStaffSerializer(review, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, review_id):
        review = self._get_owned_review(request, review_id)
        if review is None:
            return Response({'detail': 'Not allowed'}, status=403)
        review.delete()
        return Response({'detail': 'Review deleted'}, status=status.HTTP_200_OK)


class ReviewApproveView(APIView):
    permission_classes = [IsStaffAuthenticated]
    authentication_classes = [StaffSessionMiddleware]

    def post(self, request, review_id):
        review = get_object_or_404(EventReview, id=review_id)
        if review.event.company_id not in list(_staff_company_ids(request.staff)):
            return Response({'detail': 'Not allowed'}, status=403)
        review.is_approved = True
        review.is_flagged = False
        review.save(update_fields=['is_approved', 'is_flagged'])
        return Response(EventReviewStaffSerializer(review).data)


class ReviewHideView(APIView):
    permission_classes = [IsStaffAuthenticated]
    authentication_classes = [StaffSessionMiddleware]

    def post(self, request, review_id):
        review = get_object_or_404(EventReview, id=review_id)
        if review.event.company_id not in list(_staff_company_ids(request.staff)):
            return Response({'detail': 'Not allowed'}, status=403)
        review.is_approved = False
        review.save(update_fields=['is_approved'])
        return Response(EventReviewStaffSerializer(review).data)


class ReviewReplyView(APIView):
    permission_classes = [IsStaffAuthenticated]
    authentication_classes = [StaffSessionMiddleware]

    def post(self, request, review_id):
        from django.utils import timezone
        review = get_object_or_404(EventReview, id=review_id)
        if review.event.company_id not in list(_staff_company_ids(request.staff)):
            return Response({'detail': 'Not allowed'}, status=403)
        reply = (request.data.get('reply') or '').strip()
        review.staff_reply = reply
        review.staff_reply_at = timezone.now() if reply else None
        review.save(update_fields=['staff_reply', 'staff_reply_at'])
        return Response(EventReviewStaffSerializer(review).data)
