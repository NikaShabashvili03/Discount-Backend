from django.contrib import admin
from .models import CompanyStaff, Company, Staff, StaffSession


class CompanyStaffInline(admin.TabularInline):
    model = CompanyStaff
    extra = 1
    autocomplete_fields = ['staff', 'company'] 

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_verified', 'is_active', 'created_at', 'updated_at')
    search_fields = ('name',)
    inlines = [CompanyStaffInline]

@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ('firstname', 'lastname', 'email', 'mobile', 'is_active')
    search_fields = ('firstname', 'lastname', 'email')
    inlines = [CompanyStaffInline]

admin.site.register(StaffSession)