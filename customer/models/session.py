from customer.models.customer import Customer
from django.db import models
from django.utils import timezone

class CustomerSession(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    ip = models.GenericIPAddressField(null=True, blank=True)
    session_token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def is_valid(self):
        return self.expires_at > timezone.now()

    def __str__(self):
         return f"{self.created_at} / {self.expires_at}"