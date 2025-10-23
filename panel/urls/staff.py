from django.urls import path
from ..views.staff import StaffCreateView, StaffUpdateView, StaffDeleteView, StaffAdminListView, CompanyCreateView, CompanyUpdateView, LinkStaffToCompanyView, DeleteCompanyView, CompanyAdminList

urlpatterns = [
    path('create', StaffCreateView.as_view(), name='create'),
    path('update/<int:id>', StaffUpdateView.as_view(), name='update'),
    path('delete/<int:id>', StaffDeleteView.as_view(), name='delete'),
    path('company/create', CompanyCreateView.as_view(), name='company create'),
    path('company/update/<int:company_id>', CompanyUpdateView.as_view(), name='company update'),
    path('company/link/<int:company_id>', LinkStaffToCompanyView.as_view(), name='company link staff'),
    path('company/delete/<int:company_id>', DeleteCompanyView.as_view(), name='delete company'),
    path('company/list', CompanyAdminList.as_view(), name='company list for admin'),
    path('list', StaffAdminListView.as_view(), name='staff list for admin')
]