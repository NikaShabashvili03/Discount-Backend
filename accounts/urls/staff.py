from django.urls import path
from accounts.views.staff import LoginView, ProfileView, LogoutView, CompanyCreateUpdateView, StaffCreateView, StaffAdminListView

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('logout/', LogoutView.as_view(), name="logout"),
    path('create/', StaffCreateView.as_view(), name='create'),
    path('company/', CompanyCreateUpdateView.as_view(), name='company update or create'),
    path('admin/list/', StaffAdminListView.as_view(), name='staff list for admin')
]