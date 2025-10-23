from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied

class IsCustomerAuthenticated(BasePermission):
    def has_permission(self, request, view):
        if hasattr(request, "customer") and getattr(request.customer, "is_authenticated", False):
            return True
        return False

class AllowAny(BasePermission):
    def has_permission(self, request, view):
        return True