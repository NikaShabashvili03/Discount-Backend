from django.urls import path
from ..views.event import EventListView, EventDetailView

urlpatterns = [
    path('all/', EventListView.as_view(), name='event-list'),
    path('details/<int:pk>/', EventDetailView.as_view(), name='event-detail'),
]