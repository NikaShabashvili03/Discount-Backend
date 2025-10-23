from rest_framework import generics, status, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from services.models import Event
from ..serializers.event import EventListSerializer, EventDetailSerializer, AdminEventCreateSerializer, EventImageUploadSerializer, EventImage, EventImageUpdateSerializer
from services.filters.event import EventFilter
from panel.permissions import IsAdminAuthenticated
from panel.middleware import AdminSessionMiddleware
from django.shortcuts import get_object_or_404

# ---------------- ADMIN EVENTS ----------------
class AdminEventListView(generics.ListAPIView):
    queryset = Event.objects.select_related('category', 'city', 'company')
    serializer_class = EventListSerializer
    permission_classes = [IsAdminAuthenticated]
    authentication_classes = [AdminSessionMiddleware]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = EventFilter
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'base_price', 'bookings_count', 'views_count']
    ordering = ['-created_at']

class AdminEventDetailView(generics.RetrieveAPIView):
    queryset = Event.objects.select_related('category', 'city', 'company')
    serializer_class = EventDetailSerializer
    permission_classes = [IsAdminAuthenticated]
    authentication_classes = [AdminSessionMiddleware]

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

class AdminPopularEventsView(generics.ListAPIView):
    serializer_class = EventListSerializer
    permission_classes = [IsAdminAuthenticated]
    authentication_classes = [AdminSessionMiddleware]

    def get_queryset(self):
        return Event.objects.filter(is_popular=True).select_related('category', 'city', 'company')[:10]

class AdminFeaturedEventsView(generics.ListAPIView):
    serializer_class = EventListSerializer
    permission_classes = [IsAdminAuthenticated]
    authentication_classes = [AdminSessionMiddleware]

    def get_queryset(self):
        return Event.objects.filter(is_featured=True).select_related('category', 'city', 'company')[:10]

class AdminDiscountedEventsView(generics.ListAPIView):
    serializer_class = EventListSerializer
    permission_classes = [IsAdminAuthenticated]
    authentication_classes = [AdminSessionMiddleware]

    def get_queryset(self):
        now = timezone.now()
        return Event.objects.filter(
            discounts__start_date__lte=now,
            discounts__end_date__gte=now
        ).distinct().select_related('category', 'city', 'company')

class AdminEventCreateView(APIView):
    permission_classes = [IsAdminAuthenticated]
    authentication_classes = [AdminSessionMiddleware]

    def post(self, request, *args, **kwargs):
        serializer = AdminEventCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        event = serializer.save()
        return Response(
            EventDetailSerializer(event).data,
            status=status.HTTP_201_CREATED
        )

class AdminEventUpdateView(APIView):
    permission_classes = [IsAdminAuthenticated]
    authentication_classes = [AdminSessionMiddleware]

    def patch(self, request, pk, *args, **kwargs):
        event = get_object_or_404(Event, pk=pk)
        serializer = AdminEventCreateSerializer(
            event,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        updated_event = serializer.save()
        return Response(
            EventDetailSerializer(updated_event).data,
            status=status.HTTP_200_OK
        )

class AdminEventDeleteView(APIView):
    permission_classes = [IsAdminAuthenticated]
    authentication_classes = [AdminSessionMiddleware]

    def delete(self, request, pk, *args, **kwargs):
        event = get_object_or_404(Event, pk=pk)
        event.delete()
        return Response({"detail": "Event deleted successfully"}, status=status.HTTP_200_OK)

class AdminEventImageUploadView(APIView):
    permission_classes = [IsAdminAuthenticated]
    authentication_classes = [AdminSessionMiddleware]

    def post(self, request, event_id):
        event = get_object_or_404(Event, id=event_id)
        serializer = EventImageUploadSerializer(
            data=request.data, context={'event': event}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AdminEventImageDeleteAPIView(APIView):
    permission_classes = [IsAdminAuthenticated]
    authentication_classes = [AdminSessionMiddleware]

    def delete(self, request, event_id, image_id):
        event = get_object_or_404(Event, id=event_id)
        image = get_object_or_404(EventImage, id=image_id, event=event)
        image.delete()
        return Response({"details": "Image Deleted Successfuly"})

class AdminEventImageUpdateAPIView(APIView):
    permission_classes = [IsAdminAuthenticated]
    authentication_classes = [AdminSessionMiddleware]

    def put(self, request, event_id, image_id):
        return self._update(request, event_id, image_id, partial=False)

    def patch(self, request, event_id, image_id):
        return self._update(request, event_id, image_id, partial=True)

    def _update(self, request, event_id, image_id, partial):
        event = get_object_or_404(Event, id=event_id)
        image = get_object_or_404(EventImage, id=image_id, event=event)

        serializer = EventImageUpdateSerializer(
            image, data=request.data, partial=partial
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)