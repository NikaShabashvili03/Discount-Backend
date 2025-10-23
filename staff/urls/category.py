from django.urls import path
from ..views.category import CategoryListView

urlpatterns = [
    path('list', CategoryListView.as_view(), name='category-list'),
]