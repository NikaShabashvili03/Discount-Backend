from django.urls import path
from ..views.country import CountryListView

urlpatterns = [
    path('list', CountryListView.as_view(), name='country-list'),
]
