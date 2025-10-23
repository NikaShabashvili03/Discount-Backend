from django.db.models import Q
from django.utils import timezone
from rest_framework import generics, permissions, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from services.models import Event
from services.serializers.event import EventListSerializer, EventDetailSerializer, PriceCalculationSerializer
from services.filters.event import EventFilter

class EventListView(generics.ListAPIView):
    queryset = Event.objects.filter(
        city__is_active=True,
        city__country__is_active=True,
        category__is_active=True
    ).select_related('city', 'company', 'category', 'city__country')
    serializer_class = EventListSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = EventFilter
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'base_price', 'bookings_count', 'views_count']
    ordering = ['-created_at']

class EventDetailView(generics.RetrieveAPIView):
    queryset = Event.objects.filter(
        city__is_active=True,
        city__country__is_active=True,
        category__is_active=True
    ).select_related('city', 'company', 'category', 'city__country')
    serializer_class = EventDetailSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.views_count += 1
        instance.save(update_fields=['views_count'])
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

class PopularEventsView(generics.ListAPIView):
    serializer_class = EventListSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    
    def get_queryset(self):
        return Event.objects.filter(
            is_active=True,
            is_popular=True,
            city__is_active=True,
            city__country__is_active=True,
            category__is_active=True
        ).select_related('category', 'city', 'city__country', 'company')[:10]

class FeaturedEventsView(generics.ListAPIView):
    serializer_class = EventListSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    
    def get_queryset(self):
        return Event.objects.filter(
            is_active=True,
            is_featured=True,
            city__is_active=True,
            city__country__is_active=True,
            category__is_active=True
        ).select_related('category', 'city', 'city__country', 'company')[:10]

class DiscountedEventsView(generics.ListAPIView):
    serializer_class = EventListSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    
    def get_queryset(self):
        now = timezone.now()
        return Event.objects.filter(
            is_active=True,
            discounts__is_active=True,
            discounts__start_date__lte=now,
            discounts__end_date__gte=now,
            city__is_active=True,
            city__country__is_active=True,
            category__is_active=True
        ).distinct().select_related('category', 'city', 'city__country', 'company')
    

class PriceCalculationView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    
    def post(self, request):
        serializer = PriceCalculationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.to_representation(serializer.validated_data))

class SearchView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    
    def get(self, request):
        query = request.query_params.get('q', '')
        if not query:
            return Response([])
        
        events = Event.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query),
            is_active=True,
            city__is_active=True,
            city__country__is_active=True,
            category__is_active=True
        )[:10]
        
        return Response(EventListSerializer(events, many=True).data)
