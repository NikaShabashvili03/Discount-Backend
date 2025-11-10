from django.urls import path
from ..views.slider import (
    SliderUploadView,
    SliderDeleteView
)

urlpatterns = [
    path('create', SliderUploadView.as_view(), name='admin-slider-create'),
    path('delete/<int:id>', SliderDeleteView.as_view(), name='admin-slider-delete'),
]
