from rest_framework import generics, status
from rest_framework.response import Response
from panel.permissions import IsAdminAuthenticated
from ..serializers.staff import StaffSerializer, CompanyCreateSerializer, CompanySerializer, CompanyUpdateSerializer, StaffCreateSerializer, StaffUpdateSerializer
from panel.middleware import AdminSessionMiddleware
from staff.models import Staff, Company, CompanyStaff
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

class StaffDeleteView(APIView):
    permission_classes = [IsAdminAuthenticated]
    authentication_classes = [AdminSessionMiddleware]

    def delete(self, request, id, *args, **kwargs):
        staff = get_object_or_404(Staff, id=id)
        staff.delete()
        return Response({"detail": "Staff deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

class StaffUpdateView(APIView):
    permission_classes = [IsAdminAuthenticated]
    authentication_classes = [AdminSessionMiddleware]

    def put(self, request, id, *args, **kwargs):
        staff = get_object_or_404(Staff, id=id)
        serializer = StaffUpdateSerializer(
            staff, data=request.data, partial=True, context={"staff_id": staff.id}
        )
        if serializer.is_valid():
            staff = serializer.update(staff, serializer.validated_data)
            data = StaffSerializer(staff).data
            return Response(data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class StaffCreateView(APIView):
    permission_classes = [IsAdminAuthenticated]
    authentication_classes = [AdminSessionMiddleware]

    def post(self, request, *args, **kwargs):
        serializer = StaffCreateSerializer(data=request.data)
        if serializer.is_valid():
            staff = serializer.create(serializer.validated_data)
            
            staff.set_password(serializer.validated_data['password'])
            staff.save()

            data = StaffSerializer(staff).data
            return Response(data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CompanyCreateView(APIView):
    permission_classes = [IsAdminAuthenticated]
    authentication_classes = [AdminSessionMiddleware]

    def post(self, request):
        serializer = CompanyCreateSerializer(data=request.data)
        if serializer.is_valid():
            company = serializer.save()
            return Response(CompanySerializer(company).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CompanyUpdateView(APIView):
    permission_classes = [IsAdminAuthenticated]
    authentication_classes = [AdminSessionMiddleware]

    def patch(self, request, company_id):
        try:
            company = Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            return Response({"detail": "Company not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = CompanyUpdateSerializer(company, data=request.data, partial=True)
        if serializer.is_valid():
            updated_company = serializer.save()
            return Response(CompanySerializer(updated_company).data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LinkStaffToCompanyView(APIView):
    permission_classes = [IsAdminAuthenticated]
    authentication_classes = [AdminSessionMiddleware]

    def post(self, request, company_id):
        staff_ids = request.data.get("staff_ids", [])
        
        if len(staff_ids) == 0:
            return Response({"details": "Staff ids is 0"}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            company = Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            return Response({"detail": "Company not found"}, status=status.HTTP_404_NOT_FOUND)

        toggled_staff = []
        for staff_id in staff_ids:
            try:
                staff = Staff.objects.get(id=staff_id)
            except Staff.DoesNotExist:
                continue 

            link = CompanyStaff.objects.filter(company=company, staff=staff).first()
            if link:
                link.delete()
                toggled_staff.append({"staff_id": staff.id, "status": "unlinked"})
            else:
                CompanyStaff.objects.create(company=company, staff=staff, role="Member")
                toggled_staff.append({"staff_id": staff.id, "status": "linked"})

        return Response({
            "detail": "Staff linking updated",
            "results": toggled_staff
        }, status=status.HTTP_200_OK)

class DeleteCompanyView(APIView):
    permission_classes = [IsAdminAuthenticated]
    authentication_classes = [AdminSessionMiddleware]

    def delete(self, request, company_id):
        try:
            company = Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            return Response({"detail": "Company not found"}, status=status.HTTP_404_NOT_FOUND)

        company.delete()
        return Response({"detail": "Company deleted successfully"}, status=status.HTTP_200_OK)
    
class StaffAdminListView(generics.ListAPIView):
    permission_classes = [IsAdminAuthenticated]
    authentication_classes = [AdminSessionMiddleware]
    serializer_class = StaffSerializer
    queryset = Staff.objects.all()

class CompanyAdminList(generics.ListAPIView):
    permission_classes = [IsAdminAuthenticated]
    authentication_classes = [AdminSessionMiddleware]
    serializer_class = CompanySerializer
    queryset = Company.objects.all().distinct()