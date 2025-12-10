from django.urls import path
from ..views.customer import LoginView, ProfileView, LogoutView, RegisterView, GoogleLoginView

urlpatterns = [
    path('login', LoginView.as_view(), name='login'),
    path('register', RegisterView.as_view(), name='register'),
    path('profile', ProfileView.as_view(), name='profile'),
    path('logout', LogoutView.as_view(), name="logout"),
    path('google/login', GoogleLoginView.as_view(), name='google-login'),
]