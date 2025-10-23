from django.urls import path, include

urlpatterns = [
    path('auth/', include('staff.urls.staff')),
    path('category/', include('staff.urls.category')),
    path('city/', include('staff.urls.city')),
    path('country/', include('staff.urls.country')),
    path('event/', include('staff.urls.event'))
]