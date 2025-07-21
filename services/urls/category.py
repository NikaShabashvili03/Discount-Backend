from django.urls import path
from ..views.category import CategoryListView

urlpatterns = [
    path('all/', CategoryListView.as_view(), name='city-list'),
]