from django.contrib import admin
from orders.models import Order, Payment
# Register your models here.


admin.site.register(Payment)
admin.site.register(Order)
