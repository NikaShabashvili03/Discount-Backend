from django.urls import path
from ..views.service import ServiceDetailView, ServiceListView, PopularServicesView, FeaturedServicesView, DiscountedServicesView, ProviderServiceListView, ProviderServiceDetailView, ProviderStatsView, SearchView, ProviderOrderListView, PriceCalculationView

urlpatterns = [
    path('feed', ServiceListView.as_view(), name='service-list'),
    path('details/<int:pk>', ServiceDetailView.as_view(), name='service-detail'),
    path('feed/popular', PopularServicesView.as_view(), name='popular-services'),
    path('feed/featured', FeaturedServicesView.as_view(), name='featured-services'),
    path('feed/discounted', DiscountedServicesView.as_view(), name='discounted-services'),

    path('search', SearchView.as_view(), name='search'),
    path('price-calculate', PriceCalculationView.as_view(), name='price-calculate'),

    path('provider/services', ProviderServiceListView.as_view(), name='provider-service-list'),
    path('provider/services/<int:pk>', ProviderServiceDetailView.as_view(), name='provider-service-detail'),
    path('provider/orders', ProviderOrderListView.as_view(), name='provider-order-list'),
    path('provider/stats', ProviderStatsView.as_view(), name='provider-stats'),
]