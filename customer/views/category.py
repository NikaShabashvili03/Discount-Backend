from rest_framework import generics, permissions, status
from services.serializers.category import CategorySerializer
from services.models import Category

class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []