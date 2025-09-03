from django.urls import path
from accounts.views.admin import LoginView, ProfileView, LogoutView, AdminCreateView, AdminListView

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('create/', AdminCreateView.as_view(), name='admin-create'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('logout/', LogoutView.as_view(), name="logout"),
    path('list/', AdminListView.as_view(), name='staff list for admin')
]