from django.urls import path
from ..views.category import CategoryCreateUpdateView, CategoryDeleteView, CategoryAdminListView, AdminCompanyCategoryListView, AdminCompanyCategoryView

urlpatterns = [
    path('list', CategoryAdminListView.as_view(), name='category-admin-list'),
    path('upload', CategoryCreateUpdateView.as_view(), name='category-create'),
    path('delete/<int:pk>', CategoryDeleteView.as_view(), name='category-delete'),

    path('company/<int:company_id>/list', AdminCompanyCategoryListView.as_view(), name='admin-company-category-list'),  # admin
    # 🔹 Admin link/unlink category to company
    path('company-category', AdminCompanyCategoryView.as_view(), name='admin-company-category'),
]