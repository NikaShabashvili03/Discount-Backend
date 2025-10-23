from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied

class IsStaffAuthenticated(BasePermission):
    def has_permission(self, request, view):
        if hasattr(request, "staff") and getattr(request.staff, "is_authenticated", False):
            return True
        return False