from django.urls import path
from ..views.review import (
    EventReviewListView,
    EventReviewSummaryView,
    EventReviewCreateView,
    EventReviewUpdateDeleteView,
    EventReviewHelpfulToggleView,
    EventReviewFlagView,
    MyReviewForEventView,
    MyReviewsListView,
)

urlpatterns = [
    # Public read endpoints
    path('event/<int:event_id>/list', EventReviewListView.as_view(), name='customer-review-list'),
    path('event/<int:event_id>/summary', EventReviewSummaryView.as_view(), name='customer-review-summary'),

    # Authenticated customer endpoints
    path('event/<int:event_id>/create', EventReviewCreateView.as_view(), name='customer-review-create'),
    path('event/<int:event_id>/me', MyReviewForEventView.as_view(), name='customer-review-mine-for-event'),

    path('mine', MyReviewsListView.as_view(), name='customer-review-mine-all'),

    path('<int:review_id>/edit', EventReviewUpdateDeleteView.as_view(), name='customer-review-edit'),
    path('<int:review_id>/helpful', EventReviewHelpfulToggleView.as_view(), name='customer-review-helpful'),
    path('<int:review_id>/flag', EventReviewFlagView.as_view(), name='customer-review-flag'),
]
