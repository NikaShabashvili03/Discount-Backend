import django_filters
from django_filters import rest_framework as filters
from ..models import Event
from services.models.category import Category
from services.models.city import City

class EventFilter(django_filters.FilterSet):
    min_price = django_filters.NumberFilter(field_name='base_price', lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name='base_price', lookup_expr='lte')
    
    category = django_filters.ModelChoiceFilter(queryset=Category.objects.all())
    city = django_filters.ModelChoiceFilter(queryset=City.objects.all())
    
    categories = django_filters.ModelMultipleChoiceFilter(
        field_name='category',
        queryset=Category.objects.all()
    )
    
    cities = django_filters.ModelMultipleChoiceFilter(
        field_name='city',
        queryset=City.objects.all()
    )
    
    min_people = django_filters.NumberFilter(field_name='min_people', lookup_expr='lte')
    max_people = django_filters.NumberFilter(field_name='max_people', lookup_expr='gte')
    
    is_popular = django_filters.BooleanFilter()
    is_featured = django_filters.BooleanFilter()
    
    company = django_filters.NumberFilter(field_name='company__id')
    company_name = django_filters.CharFilter(
        field_name='company_name', 
        lookup_expr='icontains'
    )
    
    location = django_filters.CharFilter(field_name='location', lookup_expr='icontains')
    
    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    
    has_discount = django_filters.BooleanFilter(method='filter_has_discount')
    
    # Custom filter for services within distance (if you have lat/lng)
    # latitude = django_filters.NumberFilter(method='filter_by_distance')
    # longitude = django_filters.NumberFilter(method='filter_by_distance')
    # radius = django_filters.NumberFilter(method='filter_by_distance')
    
    class Meta:
        model = Event
        fields = {
            'name': ['exact', 'icontains'],
            'base_price': ['exact', 'gte', 'lte'],
            'views_count': ['gte', 'lte'],
            'bookings_count': ['gte', 'lte'],
        }
    
    def filter_has_discount(self, queryset, name, value):
        if value:
            from django.utils import timezone
            now = timezone.now()
            return queryset.filter(
                discounts__is_active=True,
                discounts__start_date__lte=now,
                discounts__end_date__gte=now
            ).distinct()
        return queryset