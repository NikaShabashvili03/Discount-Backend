from rest_framework import generics
from ..serializers.category import CategorySerializer
from services.models import Category
from ..models import CompanyStaff
from ..permissions import IsStaffAuthenticated
from ..middleware import StaffSessionMiddleware
from rest_framework.exceptions import PermissionDenied

class CategoryListView(generics.ListAPIView):
    serializer_class = CategorySerializer
    permission_classes = [IsStaffAuthenticated]
    authentication_classes = [StaffSessionMiddleware]

    def get_queryset(self):
        company_id = self.request.query_params.get("company_id")
        staff = self.request.user

        if not company_id:
            raise PermissionDenied("Missing company_id parameter.")

        if not CompanyStaff.objects.filter(company_id=company_id, staff=staff).exists():
            raise PermissionDenied("You do not have access to this company's categories.")

        return Category.objects.filter(companies__company_id=company_id, is_active=True)