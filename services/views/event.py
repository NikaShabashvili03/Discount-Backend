from rest_framework import generics, status, permissions, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from ..models import Event
from ..serializer.event import EventListSerializer, EventDetailSerializer, EventCreateUpdateSerializer, PriceCalculationSerializer, AdminEventCreateSerializer
from ..filters.event import EventFilter
from accounts.models.staff import Company
from accounts.permissions import IsStaffAuthenticated, IsAdminAuthenticated
from accounts.middleware import StaffSessionMiddleware, AdminSessionMiddleware
from orders.models import Order
from orders.serializers.order import OrderSerializer
from django.shortcuts import get_object_or_404

class EventListView(generics.ListAPIView):
    queryset = Event.objects.filter(is_active=True).select_related('category', 'city', 'company')
    serializer_class = EventListSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = EventFilter
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'base_price', 'bookings_count', 'views_count']
    ordering = ['-created_at']

class EventDetailView(generics.RetrieveAPIView):
    queryset = Event.objects.filter(is_active=True).select_related('category', 'city', 'company')
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
            is_popular=True
        ).select_related('category', 'city', 'company')[:10]

class FeaturedEventsView(generics.ListAPIView):
    serializer_class = EventListSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    
    def get_queryset(self):
        return Event.objects.filter(
            is_active=True,
            is_featured=True
        ).select_related('category', 'city', 'company')[:10]

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
            discounts__end_date__gte=now
        ).distinct().select_related('category', 'city', 'company')
    
# Admin Add Event
class AdminEventCreateView(APIView):
    permission_classes = [IsAdminAuthenticated]
    authentication_classes = [AdminSessionMiddleware]

    def post(self, request, *args, **kwargs):
        serializer = AdminEventCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        event = serializer.save()
        return Response(EventDetailSerializer(event).data, status=status.HTTP_201_CREATED)
    
# Company Events
class CompanyEventListView(generics.ListCreateAPIView):
    serializer_class = EventListSerializer
    permission_classes = [IsStaffAuthenticated]
    authentication_classes = [StaffSessionMiddleware]
    
    def get_queryset(self):
        return Event.objects.filter(company__user=self.request.user)
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return EventCreateUpdateSerializer
        return EventListSerializer

class CompanyEventDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = EventCreateUpdateSerializer
    permission_classes = [IsStaffAuthenticated]
    authentication_classes = [StaffSessionMiddleware]
    
    def get_queryset(self):
        return Event.objects.filter(company__user=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({"detail": "Successfully deleted"}, status=status.HTTP_200_OK)

class CompanyOrderListView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsStaffAuthenticated]
    authentication_classes = [StaffSessionMiddleware]
    
    def get_queryset(self):
        return Order.objects.filter(event__company__user=self.request.user)

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
            is_active=True
        )[:10]
        
        return Response(EventListSerializer(events, many=True).data)