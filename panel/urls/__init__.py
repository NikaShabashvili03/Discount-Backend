from django.urls import path, include

urlpatterns = [
    path('auth/', include('panel.urls.admin')),
    path('category/', include('panel.urls.category')),
    path('country/', include('panel.urls.country')),
    path('city/', include('panel.urls.city')),
    path('event/', include('panel.urls.event')),
    path('staff/', include('panel.urls.staff')),
    path('customer/', include('panel.urls.customer'))
]