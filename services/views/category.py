from rest_framework import generics, permissions, status
from ..serializer.category import CategorySerializer, CategoryCreateUpdateSerializer
from ..models import Category
from accounts.permissions import AllowAny, IsAdminAuthenticated
from accounts.middleware import AdminSessionMiddleware
from rest_framework.response import Response


class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

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