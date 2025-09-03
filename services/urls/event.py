from django.urls import path
from ..views.event import EventDetailView, EventListView, PopularEventsView, FeaturedEventsView, DiscountedEventsView, CompanyEventListView, CompanyEventDetailView, SearchView, CompanyOrderListView, PriceCalculationView, AdminEventCreateView

urlpatterns = [
    path('feed', EventListView.as_view(), name='event-list'),
    path('details/<int:pk>', EventDetailView.as_view(), name='event-detail'),
    path('feed/popular', PopularEventsView.as_view(), name='popular-events'),
    path('feed/featured', FeaturedEventsView.as_view(), name='featured-events'),
    path('feed/discounted', DiscountedEventsView.as_view(), name='discounted-events'),

    path('search', SearchView.as_view(), name='search'),
    path('price-calculate', PriceCalculationView.as_view(), name='price-calculate'),

    path('company/events', CompanyEventListView.as_view(), name='company-event-list'),
    path('company/events/<int:pk>', CompanyEventDetailView.as_view(), name='company-event-detail'),
    path('company/orders', CompanyOrderListView.as_view(), name='company-order-list'),

    path('admin/event/create', AdminEventCreateView.as_view(), name='company-create-admin')
]