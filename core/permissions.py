from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied

class AllowAny(BasePermission):
    def has_permission(self, request, view):
        return True