from rest_framework.permissions import BasePermission

class IsAuthenticated(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
class AllowAny(BasePermission):
    def has_permission(self, request, view):
        return True
    
class IsServiceProvider(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type in ['provider', 'Service Provider']