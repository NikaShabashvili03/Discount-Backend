from django.urls import path
from ..views.event import (
    EventDetailView,
    EventListView,
    PopularEventsView,
    FeaturedEventsView,
    DiscountedEventsView,
    SearchView,
    PriceCalculationView
)

urlpatterns = [
    # Customer / feed
    path('feed', EventListView.as_view(), name='event-list'),
    path('details/<int:pk>', EventDetailView.as_view(), name='event-detail'),
    path('feed/popular', PopularEventsView.as_view(), name='popular-events'),
    path('feed/featured', FeaturedEventsView.as_view(), name='featured-events'),
    path('feed/discounted', DiscountedEventsView.as_view(), name='discounted-events'),

    # Search & price
    path('search', SearchView.as_view(), name='search'),
    path('price-calculate', PriceCalculationView.as_view(), name='price-calculate'),
]
