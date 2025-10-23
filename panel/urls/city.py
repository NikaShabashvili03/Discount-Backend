from django.urls import path
from ..views.city import CityCreateUpdateView, CityDeleteView, CityAdminListView

urlpatterns = [
    path('list', CityAdminListView.as_view(), name='city-admin-list'),
    path('upload', CityCreateUpdateView.as_view(), name='city-create/update'),
    path('delete/<int:city_id>', CityDeleteView.as_view(), name='city-delete'),
]