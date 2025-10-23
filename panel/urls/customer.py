from django.urls import path
from ..views.customer import CustomerAdminListView

urlpatterns = [
    path('list', CustomerAdminListView.as_view(), name='customer list for admin'),
]