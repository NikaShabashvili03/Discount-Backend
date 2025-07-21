from django.db import models
from accounts.models import User
from decimal import Decimal
from django.core.validators import MinValueValidator, MaxValueValidator
from services.models.category import Category
from services.models.city import City
from ..utils import image_upload, validate_image
from django.core.exceptions import ValidationError


def upload_provider_logo(instance, filename):
    return image_upload(instance, filename, 'provider_logos/')

def upload_service_image(instance, filename):
    return image_upload(instance, filename, 'service_images/')

class ServiceProvider(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'user_type__in': ['provider', 'Service Provider']}
    )

    company_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to=upload_provider_logo, null=True, blank=True)
    
    is_verified = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    
    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('10.00'),
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))],
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.user.user_type not in ['provider', 'Service Provider']:
            raise ValueError("User must be a provider or service provider.")
        
        if self.logo:
            try:
                self.logo = validate_image(image_field=self.logo, max_size_kb=1200, compress_quality=75, path='provider_logos/')
            except (FileNotFoundError, ValueError, ValidationError):
                self.logo = None

        super().save(*args, **kwargs)

    def __str__(self):
        return self.company_name
    

class Service(models.Model):
    provider = models.ForeignKey(ServiceProvider, on_delete=models.CASCADE, related_name="services")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="services")
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="services")

    name = models.CharField(max_length=200)
    description = models.TextField()

    base_price = models.DecimalField(max_digits=10, decimal_places=2)

    price_per_person = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="Additional price per person"
    )

    min_people = models.IntegerField(default=1)
    max_people = models.IntegerField(default=50)

    location = models.CharField(max_length=300)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    is_popular = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)

    views_count = models.IntegerField(default=0)
    bookings_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.id} | {self.name}"
    
    def calculate_price(self, people_count):
        if people_count < self.min_people:
            people_count = self.min_people
        elif people_count > self.max_people:
            people_count = self.max_people
        
        total_price = self.base_price + (self.price_per_person * (people_count - 1))
        return total_price
    

class ServiceImage(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to=upload_service_image)
    alt_text = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        if self.image:
            try:
                self.image = validate_image(image_field=self.image, max_size_kb=1200, compress_quality=75, path='service_images/')
            except (FileNotFoundError, ValueError, ValidationError):
                self.image = None
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return f"{self.service.name} | {self.alt_text} | {self.image}"

class Discount(models.Model):
    DISCOUNT_TYPES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]
    
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='discounts')
    name = models.CharField(max_length=100)
    
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    
    is_active = models.BooleanField(default=True)
    max_uses = models.IntegerField(null=True, blank=True)
    used_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} - {self.service.name}"
    
    def is_valid(self):
        from django.utils import timezone
        now = timezone.now()
        return (
            self.is_active and 
            self.start_date <= now <= self.end_date and
            (self.max_uses is None or self.used_count < self.max_uses)
        )
    


