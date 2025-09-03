from django.urls import path
from accounts.views.customer import LoginView, ProfileView, LogoutView, RegisterView, CustomerAdminListView

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('logout/', LogoutView.as_view(), name="logout"),
    path('admin/list/', CustomerAdminListView.as_view(), name='customer list for admin'),
]