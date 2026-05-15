from django.contrib import admin
from services.models import (
    Category, City, Event, EventImage, Discount, Country, CompanyCategory,
    EventReview, EventReviewHelpful,
)


admin.site.register(Category)
admin.site.register(City)
admin.site.register(Event)
admin.site.register(EventImage)
admin.site.register(Discount)
admin.site.register(Country)
admin.site.register(CompanyCategory)


@admin.register(EventReview)
class EventReviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'event', 'customer', 'rating', 'mark', 'is_approved', 'is_flagged', 'created_at')
    list_filter = ('mark', 'is_approved', 'is_flagged', 'rating')
    search_fields = ('event__name', 'customer__email', 'title', 'comment')
    list_editable = ('is_approved', 'is_flagged')


@admin.register(EventReviewHelpful)
class EventReviewHelpfulAdmin(admin.ModelAdmin):
    list_display = ('id', 'review', 'customer', 'created_at')
    search_fields = ('review__event__name', 'customer__email')