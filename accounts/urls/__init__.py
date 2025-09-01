from django.urls import path, include

urlpatterns = [
    path('admin/', include('accounts.urls.admin')),
    path('staff/', include('accounts.urls.staff')),
    path('customer/', include('accounts.urls.customer')),
]