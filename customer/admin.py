from django.contrib import admin
from customer.models import BlackList, Customer, CustomerSession

admin.site.register(BlackList)

admin.site.register(Customer)
admin.site.register(CustomerSession)
