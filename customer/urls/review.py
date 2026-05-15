from django.urls import path

from ..views.review import ReviewCreateView, ReviewListView

urlpatterns = [
    path('event/<int:event_id>/list', ReviewListView.as_view(), name='customer-review-list'),
    path('event/<int:event_id>/create', ReviewCreateView.as_view(), name='customer-review-create'),
]
