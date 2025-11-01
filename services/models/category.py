from django.db import models
from ..utils import image_upload, validate_image
from django.core.exceptions import ValidationError
from staff.models import Company

def upload_category_icon(instance, filename):
    return image_upload(instance, filename, 'category_icons/')

class Category(models.Model):
    ACTIVITY_CHOICE = (
        ('water', 'Water activity'),
        ('land', 'Land activity')
    )

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    icon = models.ImageField(upload_to=upload_category_icon, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    color = models.CharField(max_length=50, blank=True, null=True)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    activity = models.CharField(max_length=25, choices=ACTIVITY_CHOICE)

    def save(self, *args, **kwargs):
        if self.icon:
            try:
                self.icon = validate_image(image_field=self.icon, max_size_kb=1200, compress_quality=75, path='category_icons/')
            except (FileNotFoundError, ValueError, ValidationError):
                self.icon = None
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

class CompanyCategory(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="companies")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="categories")