from django.urls import path
from ..views.event import (
    CompanyOrderListView,
    CompanyEventCreateView,
    CompanyEventUpdateView,
    CompanyEventDeleteView,
    CompanyEventListView,
    CompanyEventDetailView,
    CompanyEventImageUploadView,
    CompanyEventImageDeleteAPIView,
    CompanyEventImageUpdateAPIView,
)

urlpatterns = [
    path('<int:event_id>/images', CompanyEventImageUploadView.as_view(), name='company-event-image-upload'),
    path('<int:event_id>/images/delete/<int:image_id>', CompanyEventImageDeleteAPIView.as_view(), name='company-event-image-delete'),
    path('<int:event_id>/images/update/<int:image_id>', CompanyEventImageUpdateAPIView.as_view(), name='company-event-image-update'),
    path('<int:company_id>/list', CompanyEventListView.as_view(), name='company-event-list'),
    path('<int:company_id>/create', CompanyEventCreateView.as_view(), name='company-event-create'),
    path('details/<int:event_id>', CompanyEventDetailView.as_view(), name='company-event-detail'),
    path('update/<int:event_id>', CompanyEventUpdateView.as_view(), name='company-event-update'),
    path('delete/<int:event_id>', CompanyEventDeleteView.as_view(), name='company-event-delete'),
    path('orders/<int:company_id>', CompanyOrderListView.as_view(), name='company-order-list'),
]
