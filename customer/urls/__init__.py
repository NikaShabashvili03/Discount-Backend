from django.urls import path, include

urlpatterns = [
    path('auth/', include('customer.urls.customer')),
    path('category/', include('customer.urls.category')),
    path('country/', include('customer.urls.country')),
    path('city/', include('customer.urls.city')),
    path('event/', include('customer.urls.event')),
]