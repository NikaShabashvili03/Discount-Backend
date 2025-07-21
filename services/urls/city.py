from django.urls import path
from ..views.city import CityListView

urlpatterns = [
    path('all/', CityListView.as_view(), name='city-list'),
]