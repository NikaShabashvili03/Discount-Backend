from django.urls import path, include

urlpatterns = [
    path('city/', include('services.urls.city')),
    path('category/', include('services.urls.category')),
    path('service/', include('services.urls.service'))
]