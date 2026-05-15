from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from services.models import Event, EventReview, EventReviewHelpful
from services.serializers.review import (
    EventReviewSerializer,
    EventReviewCreateSerializer,
    EventRatingSummarySerializer,
)
from ..middleware import CustomerSessionMiddleware
from ..permissions import IsCustomerAuthenticated, AllowAny


def _approved_reviews_qs(event_id=None):
    qs = EventReview.objects.filter(is_approved=True, is_flagged=False).select_related('customer', 'event')
    if event_id is not None:
        qs = qs.filter(event_id=event_id)
    return qs


def _rating_summary(event_id):
    qs = EventReview.objects.filter(event_id=event_id, is_approved=True, is_flagged=False)
    agg = qs.aggregate(avg=Avg('rating'), count=Count('id'))
    counts = qs.values('rating').annotate(c=Count('id'))
    distribution = {str(i): 0 for i in range(1, 6)}
    for row in counts:
        distribution[str(row['rating'])] = row['c']
    marks = qs.aggregate(
        good=Count('id', filter=Q(mark='good')),
        bad=Count('id', filter=Q(mark='bad')),
        neutral=Count('id', filter=Q(mark='neutral')),
    )
    return {
        'average_rating': round(agg['avg'] or 0, 2),
        'rating_count': agg['count'] or 0,
        'good_count': marks['good'] or 0,
        'bad_count': marks['bad'] or 0,
        'neutral_count': marks['neutral'] or 0,
        'distribution': distribution,
    }


class EventReviewListView(generics.ListAPIView):
    """Public list of approved reviews for a specific event."""
    serializer_class = EventReviewSerializer
    permission_classes = [AllowAny]
    authentication_classes = [CustomerSessionMiddleware]

    def get_queryset(self):
        event_id = self.kwargs['event_id']
        ordering = self.request.query_params.get('ordering', '-created_at')
        allowed_ordering = {
            'created_at', '-created_at',
            'rating', '-rating',
            'helpful_count', '-helpful_count',
        }
        if ordering not in allowed_ordering:
            ordering = '-created_at'
        return _approved_reviews_qs(event_id=event_id).order_by(ordering)


class EventReviewSummaryView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, event_id):
        get_object_or_404(Event, id=event_id)
        data = _rating_summary(event_id)
        return Response(EventRatingSummarySerializer(data).data)


class EventReviewCreateView(APIView):
    """Authenticated customers can create or upsert their review for an event."""
    permission_classes = [IsCustomerAuthenticated]
    authentication_classes = [CustomerSessionMiddleware]

    def post(self, request, event_id):
        event = get_object_or_404(Event, id=event_id)
        serializer = EventReviewCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        review, _created = EventReview.objects.update_or_create(
            event=event,
            customer=request.customer,
            defaults=serializer.validated_data,
        )
        return Response(
            EventReviewSerializer(review, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


class EventReviewUpdateDeleteView(APIView):
    permission_classes = [IsCustomerAuthenticated]
    authentication_classes = [CustomerSessionMiddleware]

    def _get_owned(self, request, review_id):
        return get_object_or_404(EventReview, id=review_id, customer=request.customer)

    def patch(self, request, review_id):
        review = self._get_owned(request, review_id)
        serializer = EventReviewCreateSerializer(review, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(EventReviewSerializer(review, context={'request': request}).data)

    def put(self, request, review_id):
        review = self._get_owned(request, review_id)
        serializer = EventReviewCreateSerializer(review, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(EventReviewSerializer(review, context={'request': request}).data)

    def delete(self, request, review_id):
        review = self._get_owned(request, review_id)
        review.delete()
        return Response({'detail': 'Review deleted'}, status=status.HTTP_200_OK)


class EventReviewHelpfulToggleView(APIView):
    permission_classes = [IsCustomerAuthenticated]
    authentication_classes = [CustomerSessionMiddleware]

    def post(self, request, review_id):
        review = get_object_or_404(EventReview, id=review_id, is_approved=True, is_flagged=False)
        vote, created = EventReviewHelpful.objects.get_or_create(
            review=review, customer=request.customer
        )
        if not created:
            vote.delete()
            review.helpful_count = max(0, review.helpful_count - 1)
            review.save(update_fields=['helpful_count'])
            return Response({
                'helpful': False,
                'helpful_count': review.helpful_count,
            })
        review.helpful_count += 1
        review.save(update_fields=['helpful_count'])
        return Response({
            'helpful': True,
            'helpful_count': review.helpful_count,
        })


class MyReviewForEventView(APIView):
    permission_classes = [IsCustomerAuthenticated]
    authentication_classes = [CustomerSessionMiddleware]

    def get(self, request, event_id):
        review = EventReview.objects.filter(event_id=event_id, customer=request.customer).first()
        if not review:
            return Response({'detail': 'No review yet'}, status=status.HTTP_404_NOT_FOUND)
        return Response(EventReviewSerializer(review, context={'request': request}).data)


class MyReviewsListView(generics.ListAPIView):
    serializer_class = EventReviewSerializer
    permission_classes = [IsCustomerAuthenticated]
    authentication_classes = [CustomerSessionMiddleware]

    def get_queryset(self):
        return EventReview.objects.filter(customer=self.request.customer).select_related('event')

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['request'] = self.request
        return ctx


class EventReviewFlagView(APIView):
    """Any authenticated customer can flag a review for moderation."""
    permission_classes = [IsCustomerAuthenticated]
    authentication_classes = [CustomerSessionMiddleware]

    def post(self, request, review_id):
        review = get_object_or_404(EventReview, id=review_id)
        reason = (request.data.get('reason') or '').strip()[:255]
        review.is_flagged = True
        if reason:
            review.flag_reason = reason
        review.save(update_fields=['is_flagged', 'flag_reason'])
        return Response({'detail': 'Review flagged for moderation'})
