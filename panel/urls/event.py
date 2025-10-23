from django.urls import path
from ..views.event import (
    AdminEventCreateView,
    AdminEventListView,
    AdminEventDetailView,
    AdminPopularEventsView,
    AdminFeaturedEventsView,
    AdminDiscountedEventsView,
    AdminEventUpdateView,
    AdminEventDeleteView,
    AdminEventImageUploadView,
    AdminEventImageDeleteAPIView,
    AdminEventImageUpdateAPIView
)

urlpatterns = [
    path('feed', AdminEventListView.as_view(), name='admin-event-list'),
    path('details/<int:pk>', AdminEventDetailView.as_view(), name='admin-event-detail'),
    path('feed/popular', AdminPopularEventsView.as_view(), name='admin-popular-events'),
    path('feed/featured', AdminFeaturedEventsView.as_view(), name='admin-featured-events'),
    path('feed/discounted', AdminDiscountedEventsView.as_view(), name='admin-discounted-events'),
    path('create', AdminEventCreateView.as_view(), name='admin-event-create'),
    path('update/<int:pk>', AdminEventUpdateView.as_view(), name='admin-event-update'),
    path('delete/<int:pk>', AdminEventDeleteView.as_view(), name='admin-event-delete'),
    path('<int:event_id>/images', AdminEventImageUploadView.as_view(), name='admin-event-image-upload'),
    path('<int:event_id>/images/delete/<int:image_id>', AdminEventImageDeleteAPIView.as_view(), name='admin-event-image-delete'),
    path('<int:event_id>/images/update/<int:image_id>', AdminEventImageUpdateAPIView.as_view(), name='admin-event-image-update'),
]
