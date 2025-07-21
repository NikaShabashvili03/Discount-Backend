from django.contrib import admin
from services.models import Category, City, ServiceProvider, Service, ServiceImage, Discount



admin.site.register(Category)
admin.site.register(City)
admin.site.register(ServiceProvider)
admin.site.register(Service)
admin.site.register(ServiceImage)
admin.site.register(Discount)
