from django.urls import path
from ..views.country import CountryCreateUpdateView, CountryDeleteView, CountryAdminListView

urlpatterns = [
    path('list', CountryAdminListView.as_view(), name='country-admin-list'),
    path('upload', CountryCreateUpdateView.as_view(), name='country-update-create'),
    path('delete/<int:country_id>', CountryDeleteView.as_view(), name='country-delete'),
]
