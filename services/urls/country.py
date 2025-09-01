from django.urls import path
from ..views.country import CountryListView, CountryCreateUpdateView

urlpatterns = [
    path('list/', CountryListView.as_view(), name='country-list'),
    path('', CountryCreateUpdateView.as_view(), name='country-update-create')
    
]
