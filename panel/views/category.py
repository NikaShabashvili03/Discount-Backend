from rest_framework import generics, permissions, status
from ..serializers.staff import CompanySerializer
from ..serializers.category import CategorySerializer, CategoryCreateUpdateSerializer
from services.models import Category, CompanyCategory
from panel.middleware import AdminSessionMiddleware
from rest_framework.response import Response
from rest_framework.views import APIView
from staff.models import Company
from django.shortcuts import get_object_or_404
from panel.permissions import IsAdminAuthenticated


class CategoryAdminListView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminAuthenticated]
    authentication_classes = [AdminSessionMiddleware]

class CategoryCreateUpdateView(generics.GenericAPIView):
    serializer_class = CategoryCreateUpdateSerializer
    permission_classes = [IsAdminAuthenticated]
    authentication_classes = [AdminSessionMiddleware]
    queryset = Category.objects.all()

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if Category.objects.filter(name=serializer.validated_data['name']).exists():
            return Response(
                {"error": "Category with this name already exists."},
                status=status.HTTP_400_BAD_REQUEST
            )

        category = serializer.save()
        return Response(CategorySerializer(category).data, status=status.HTTP_201_CREATED)

    def patch(self, request, pk=None, *args, **kwargs):
        category_id = request.data.get("category_id")
        if not category_id:
            return Response({"error": "category_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            category = Category.objects.get(pk=category_id)
        except Category.DoesNotExist:
            return Response({"error": "Category not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(category, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        if "name" in serializer.validated_data:
            if Category.objects.filter(
                name=serializer.validated_data["name"]
            ).exclude(pk=category.pk).exists():
                return Response(
                    {"error": "Category with this name already exists."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        category = serializer.save()
        return Response(CategorySerializer(category).data, status=status.HTTP_200_OK)
    
class CategoryDeleteView(APIView):
    permission_classes = [IsAdminAuthenticated]
    authentication_classes = [AdminSessionMiddleware]

    def delete(self, request, pk, *args, **kwargs):
        try:
            category = Category.objects.get(pk=pk)
        except Category.DoesNotExist:
            return Response({"error": "Category not found."}, status=status.HTTP_404_NOT_FOUND)

        category.delete()
        return Response({"detail": "Category deleted successfully."}, status=status.HTTP_200_OK)

class AdminCompanyFeedByCategory(APIView):
    permission_classes = [IsAdminAuthenticated]
    authentication_classes = [AdminSessionMiddleware]

    def get(self, request, category_id, *args, **kwargs):
        if not category_id:
            return Response(
                {"error": "category_id is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        category = get_object_or_404(Category, id=category_id)

        feeds = Company.objects.filter(categories__category=category).distinct()
        serializer = CompanySerializer(feeds, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    
class AdminCompanyCategoryListView(generics.ListAPIView):
    serializer_class = CategorySerializer
    permission_classes = [IsAdminAuthenticated]
    authentication_classes = [AdminSessionMiddleware]

    def get_queryset(self):
        company_id = self.kwargs.get("company_id")
        return Category.objects.filter(companies__company_id=company_id)

    def list(self, request, *args, **kwargs):
        company_id = self.kwargs.get("company_id")
        
        company = Company.objects.filter(pk=company_id).first()
        if not company:
            return Response(
                {"error": "Company not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class AdminCompanyCategoryView(APIView):
    permission_classes = [IsAdminAuthenticated]
    authentication_classes = [AdminSessionMiddleware]

    def post(self, request, *args, **kwargs):
        company_id = request.data.get("company_id")
        category_id = request.data.get("category_id")

        if not company_id or not category_id:
            return Response(
                {"error": "company_id and category_id are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        company = get_object_or_404(Company, pk=company_id)
        category = get_object_or_404(Category, pk=category_id)

        obj, created = CompanyCategory.objects.get_or_create(
            company=company, category=category
        )

        if not created:
            return Response(
                {"error": "Category already linked to this company."},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {"detail": f"Category '{category.name}' linked to company '{company.name}'."},
            status=status.HTTP_201_CREATED
        )

    def delete(self, request, *args, **kwargs):
        company_id = request.data.get("company_id")
        category_id = request.data.get("category_id")

        if not company_id or not category_id:
            return Response(
                {"error": "company_id and category_id are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            link = CompanyCategory.objects.get(
                company_id=company_id, category_id=category_id
            )
        except CompanyCategory.DoesNotExist:
            return Response(
                {"error": "Link between company and category not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        link.delete()
        return Response(
            {"detail": "Category unlinked from company successfully."},
            status=status.HTTP_200_OK
        )