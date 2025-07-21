from django.contrib import admin
from accounts.models import User, Session, BlackList

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        'email',
        'firstname',
        'lastname',
        'last_login',
    )
    search_fields = ('email', 'firstname', 'lastname')
    ordering = ('-last_login',)

admin.site.register(Session)
admin.site.register(BlackList)