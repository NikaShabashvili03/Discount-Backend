from django.contrib import admin
from accounts.models import Admin, AdminSession, BlackList, Company, Staff, StaffSession, Customer, CustomerSession

@admin.register(Admin)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        'email',
        'firstname',
        'lastname',
        'last_login',
    )
    search_fields = ('email', 'firstname', 'lastname')
    ordering = ('-last_login',)

admin.site.register(AdminSession)
admin.site.register(BlackList)


admin.site.register(Staff)
admin.site.register(StaffSession)
admin.site.register(Company)

admin.site.register(Customer)
admin.site.register(CustomerSession)