from django.urls import path
from ..views.review import (
    CompanyReviewListView,
    EventReviewListForStaffView,
    EventReviewSummaryForStaffView,
    ReviewModerationView,
    ReviewApproveView,
    ReviewHideView,
    ReviewReplyView,
)

urlpatterns = [
    path('company/<int:company_id>/list', CompanyReviewListView.as_view(), name='staff-company-review-list'),
    path('event/<int:event_id>/list', EventReviewListForStaffView.as_view(), name='staff-event-review-list'),
    path('event/<int:event_id>/summary', EventReviewSummaryForStaffView.as_view(), name='staff-event-review-summary'),
    path('<int:review_id>', ReviewModerationView.as_view(), name='staff-review-detail'),
    path('<int:review_id>/approve', ReviewApproveView.as_view(), name='staff-review-approve'),
    path('<int:review_id>/hide', ReviewHideView.as_view(), name='staff-review-hide'),
    path('<int:review_id>/reply', ReviewReplyView.as_view(), name='staff-review-reply'),
]
