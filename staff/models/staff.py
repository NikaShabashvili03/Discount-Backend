from django.db import models
from django.contrib.auth.models import AbstractBaseUser

class Staff(AbstractBaseUser):
    email = models.EmailField()
    firstname = models.CharField(max_length=255)
    lastname = models.CharField(max_length=255)
    country = models.CharField(max_length=100)
    mobile = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['firstname', 'lastname']

    def save(self, *args, **kwargs):
        self.firstname = self.firstname.capitalize()
        self.lastname = self.lastname.capitalize()
        if self.pk is None:
            self.set_password(self.password)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.firstname}"

class Company(models.Model):
    name = models.CharField(max_length=200)
    founded_year = models.PositiveIntegerField()
    is_verified = models.BooleanField(default=False)
    description = models.TextField(blank=True, null=True)

    is_verified = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    email = models.EmailField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)

    facebook = models.URLField(blank=True, null=True)
    instagram = models.URLField(blank=True, null=True)
    twitter = models.URLField(blank=True, null=True)

    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    
class CompanyStaff(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name="company_links")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="staff_links")

    role = models.CharField(max_length=100, blank=True, null=True)
    joined_at = models.DateField(auto_now_add=True)

    class Meta:
        unique_together = ('staff', 'company')