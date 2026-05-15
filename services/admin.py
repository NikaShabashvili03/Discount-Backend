from django.contrib import admin
from services.models import (
    Category, City, Event, EventImage, Discount, Country, CompanyCategory, Review,
)


admin.site.register(Category)
admin.site.register(City)
admin.site.register(Event)
admin.site.register(EventImage)
admin.site.register(Discount)
admin.site.register(Country)
admin.site.register(CompanyCategory)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'event', 'customer', 'rating', 'created_at')
    list_filter = ('rating',)
    search_fields = ('event__name', 'customer__email', 'comment')
