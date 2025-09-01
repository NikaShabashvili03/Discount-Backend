from django.urls import path, include

urlpatterns = [
    path('city/', include('services.urls.city')),
    path('country/', include('services.urls.country')),
    path('category/', include('services.urls.category')),
    path('event/', include('services.urls.event')),
]