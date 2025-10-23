from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied

class IsAdminAuthenticated(BasePermission):
    def has_permission(self, request, view):
        if hasattr(request, "admin") and getattr(request.admin, "is_authenticated", False):
            return True
        return False