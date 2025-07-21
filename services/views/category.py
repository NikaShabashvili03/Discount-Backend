from rest_framework import generics, permissions
from ..serializer.category import CategorySerializer
from ..models import Category



class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []