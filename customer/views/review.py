from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from services.models import Event, EventReview, EventReviewHelpful
from services.serializers.review import (
    EventRatingSummarySerializer,
    EventReviewCreateSerializer,
    EventReviewSerializer,
)
from ..middleware import CustomerSessionMiddleware
from ..permissions import AllowAny, IsCustomerAuthenticated


def _visible_reviews_for(event_id):
    return EventReview.objects.filter(
        event_id=event_id, is_approved=True, is_flagged=False
    ).select_related('customer')


def _build_summary(event_id):
    qs = _visible_reviews_for(event_id)
    agg = qs.aggregate(
        average_rating=Avg('rating'),
        rating_count=Count('id'),
        good_count=Count('id', filter=Q(mark='good')),
        bad_count=Count('id', filter=Q(mark='bad')),
        neutral_count=Count('id', filter=Q(mark='neutral')),
    )
    distribution = {str(i): 0 for i in range(1, 6)}
    for row in qs.values('rating').annotate(n=Count('id')):
        distribution[str(row['rating'])] = row['n']
    avg = agg['average_rating']
    return {
        'average_rating': round(avg, 2) if avg is not None else 0,
        'rating_count': agg['rating_count'] or 0,
        'good_count': agg['good_count'] or 0,
        'bad_count': agg['bad_count'] or 0,
        'neutral_count': agg['neutral_count'] or 0,
        'distribution': distribution,
    }


class EventReviewListView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [CustomerSessionMiddleware]

    def get(self, request, event_id):
        get_object_or_404(Event, id=event_id)
        reviews = _visible_reviews_for(event_id)
        return Response(
            EventReviewSerializer(reviews, many=True, context={'request': request}).data
        )


class EventReviewSummaryView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, event_id):
        get_object_or_404(Event, id=event_id)
        return Response(EventRatingSummarySerializer(_build_summary(event_id)).data)


class EventReviewCreateView(APIView):
    permission_classes = [IsCustomerAuthenticated]
    authentication_classes = [CustomerSessionMiddleware]

    def post(self, request, event_id):
        event = get_object_or_404(Event, id=event_id)
        serializer = EventReviewCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # unique_together = (event, customer) — re-submitting updates the row.
        review, _ = EventReview.objects.update_or_create(
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
        return get_object_or_404(
            EventReview, id=review_id, customer=request.customer
        )

    def patch(self, request, review_id):
        review = self._get_owned(request, review_id)
        serializer = EventReviewCreateSerializer(review, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            EventReviewSerializer(review, context={'request': request}).data
        )

    def put(self, request, review_id):
        review = self._get_owned(request, review_id)
        serializer = EventReviewCreateSerializer(review, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            EventReviewSerializer(review, context={'request': request}).data
        )

    def delete(self, request, review_id):
        self._get_owned(request, review_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class EventReviewHelpfulToggleView(APIView):
    permission_classes = [IsCustomerAuthenticated]
    authentication_classes = [CustomerSessionMiddleware]

    def post(self, request, review_id):
        review = get_object_or_404(EventReview, id=review_id)
        existing = EventReviewHelpful.objects.filter(
            review=review, customer=request.customer
        ).first()
        if existing:
            existing.delete()
            review.helpful_count = max(review.helpful_count - 1, 0)
            review.save(update_fields=['helpful_count'])
            return Response({'helpful': False, 'helpful_count': review.helpful_count})

        EventReviewHelpful.objects.create(review=review, customer=request.customer)
        review.helpful_count += 1
        review.save(update_fields=['helpful_count'])
        return Response({'helpful': True, 'helpful_count': review.helpful_count})


class MyReviewForEventView(APIView):
    permission_classes = [IsCustomerAuthenticated]
    authentication_classes = [CustomerSessionMiddleware]

    def get(self, request, event_id):
        review = EventReview.objects.filter(
            event_id=event_id, customer=request.customer
        ).select_related('customer').first()
        if not review:
            return Response(
                {'detail': 'No review yet'}, status=status.HTTP_404_NOT_FOUND
            )
        return Response(
            EventReviewSerializer(review, context={'request': request}).data
        )


class MyReviewsListView(APIView):
    permission_classes = [IsCustomerAuthenticated]
    authentication_classes = [CustomerSessionMiddleware]

    def get(self, request):
        reviews = EventReview.objects.filter(
            customer=request.customer
        ).select_related('customer', 'event')
        return Response(
            EventReviewSerializer(reviews, many=True, context={'request': request}).data
        )


class EventReviewFlagView(APIView):
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
