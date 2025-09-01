from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied

class IsAdminAuthenticated(BasePermission):
    def has_permission(self, request, view):
        if hasattr(request, "admin") and getattr(request.admin, "is_authenticated", False):
            return True
        return False

class IsStaffAuthenticated(BasePermission):
    def has_permission(self, request, view):
        if hasattr(request, "staff") and getattr(request.staff, "is_authenticated", False):
            return True
        return False

class IsCustomerAuthenticated(BasePermission):
    def has_permission(self, request, view):
        if hasattr(request, "customer") and getattr(request.customer, "is_authenticated", False):
            return True
        return False

class AllowAny(BasePermission):
    def has_permission(self, request, view):
        return True