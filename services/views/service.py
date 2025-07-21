from rest_framework import generics, status, permissions, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from ..models import Service, ServiceProvider
from ..serializer.service import ServiceListSerializer, ServiceDetailSerializer, ServiceCreateUpdateSerializer, ProviderStatsSerializer, PriceCalculationSerializer
from ..filters.service import ServiceFilter
from accounts.permissions import IsServiceProvider
from orders.models import Order
from orders.serializers.order import OrderSerializer
from django.shortcuts import get_object_or_404

class ServiceListView(generics.ListAPIView):
    queryset = Service.objects.filter(is_active=True).select_related('category', 'city', 'provider')
    serializer_class = ServiceListSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ServiceFilter
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'base_price', 'bookings_count', 'views_count']
    ordering = ['-created_at']

class ServiceDetailView(generics.RetrieveAPIView):
    queryset = Service.objects.filter(is_active=True).select_related('category', 'city', 'provider')
    serializer_class = ServiceDetailSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.views_count += 1
        instance.save(update_fields=['views_count'])
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

class PopularServicesView(generics.ListAPIView):
    serializer_class = ServiceListSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    
    def get_queryset(self):
        return Service.objects.filter(
            is_active=True,
            is_popular=True
        ).select_related('category', 'city', 'provider')[:10]

class FeaturedServicesView(generics.ListAPIView):
    serializer_class = ServiceListSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    
    def get_queryset(self):
        return Service.objects.filter(
            is_active=True,
            is_featured=True
        ).select_related('category', 'city', 'provider')[:10]

class DiscountedServicesView(generics.ListAPIView):
    serializer_class = ServiceListSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    
    def get_queryset(self):
        now = timezone.now()
        return Service.objects.filter(
            is_active=True,
            discounts__is_active=True,
            discounts__start_date__lte=now,
            discounts__end_date__gte=now
        ).distinct().select_related('category', 'city', 'provider')
    
# Provider Serrvice
class ProviderServiceListView(generics.ListCreateAPIView):
    serializer_class = ServiceListSerializer
    permission_classes = [IsServiceProvider]
    
    def get_queryset(self):
        return Service.objects.filter(provider__user=self.request.user)
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ServiceCreateUpdateSerializer
        return ServiceListSerializer

class ProviderServiceDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ServiceCreateUpdateSerializer
    permission_classes = [IsServiceProvider]
    
    def get_queryset(self):
        return Service.objects.filter(provider__user=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({"detail": "Successfully deleted"}, status=status.HTTP_200_OK)

class ProviderOrderListView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsServiceProvider]
    
    def get_queryset(self):
        return Order.objects.filter(service__provider__user=self.request.user)

class ProviderStatsView(APIView):
    permission_classes = [IsServiceProvider]
    
    def get(self, request):
        user = request.user

        from django.shortcuts import get_object_or_404
        provider = get_object_or_404(ServiceProvider, user=user)
        
        # Get date range
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            start_date = timezone.datetime.fromisoformat(start_date)
        else:
            start_date = timezone.now() - timedelta(days=30)
        
        if end_date:
            end_date = timezone.datetime.fromisoformat(end_date)
        else:
            end_date = timezone.now()
        
        orders = Order.objects.filter(
            service__provider=provider,
            created_at__range=[start_date, end_date]
        )
        
        stats = {
            'total_services': provider.services.filter(is_active=True).count(),
            'total_orders': orders.count(),
            'total_revenue': orders.aggregate(Sum('total_price'))['total_price__sum'] or Decimal('0.00'),
            'commission_owed': orders.aggregate(Sum('commission_amount'))['commission_amount__sum'] or Decimal('0.00'),
            'active_orders': orders.filter(status='confirmed').count(),
            'completed_orders': orders.filter(status='completed').count(),
            'popular_services': list(provider.services.filter(is_active=True).order_by('-bookings_count')[:5].values('name', 'bookings_count'))
        }
        
        return Response(ProviderStatsSerializer(stats).data)
    
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
        
        services = Service.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query),
            is_active=True
        )[:10]
        
        return Response(ServiceListSerializer(services, many=True).data)