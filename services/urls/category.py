from django.urls import path
from ..views.category import CategoryListView, CategoryCreateUpdateView

urlpatterns = [
    path('all/', CategoryListView.as_view(), name='city-list'),
    path('', CategoryCreateUpdateView.as_view(), name='city-create'),
]