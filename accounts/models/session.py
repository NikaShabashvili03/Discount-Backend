from accounts.models.admin import Admin
from accounts.models.staff import Staff
from accounts.models.customer import Customer
from django.db import models

class AdminSession(models.Model):
    admin = models.ForeignKey(Admin, on_delete=models.CASCADE)
    ip = models.GenericIPAddressField(null=True, blank=True)
    session_token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    def is_valid(self):
         return f"{self.session_token}"
    
    def __str__(self):
         return f"{self.created_at} / {self.expires_at}"
    
class StaffSession(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    ip = models.GenericIPAddressField(null=True, blank=True)
    session_token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def is_valid(self):
         return f"{self.session_token}"
    
    def __str__(self):
         return f"{self.created_at} / {self.expires_at}"
    
class CustomerSession(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    ip = models.GenericIPAddressField(null=True, blank=True)
    session_token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def is_valid(self):
         return f"{self.session_token}"
    
    def __str__(self):
         return f"{self.created_at} / {self.expires_at}"