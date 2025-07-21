from django.db import models
from django.contrib.auth.models import AbstractBaseUser
from django.db.models import Avg

class User(AbstractBaseUser):
    USER_TYPES = [
        ('customer', 'Customer'),
        ('provider', 'Service Provider'),
    ]

    user_type = models.CharField(max_length=20, choices=USER_TYPES, default='customer')

    firstname = models.CharField(max_length=255)
    lastname = models.CharField(max_length=255)
    country = models.CharField(max_length=100)
    mobile = models.CharField(max_length=20)

    email = models.EmailField(unique=True)
    email_verified_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    last_login = models.DateTimeField(null=True, blank=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['firstname', 'lastname']

    def save(self, *args, **kwargs):
        self.firstname = self.firstname.capitalize()
        self.lastname = self.lastname.capitalize()
        if self.pk is None: 
            self.set_password(self.password) 
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.firstname} - {self.lastname}"
    

