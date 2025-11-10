from django.urls import path
from ..views.slider import (
    SliderListView,
)

urlpatterns = [
    path('feed', SliderListView.as_view(), name='slider-list')
]
