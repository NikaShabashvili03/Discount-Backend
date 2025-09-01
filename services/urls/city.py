from django.urls import path
from ..views.city import CityListView, CityCreateUpdateView

urlpatterns = [
    path('list/', CityListView.as_view(), name='city-list'),
    path('', CityCreateUpdateView.as_view(), name='city-create/update')
]