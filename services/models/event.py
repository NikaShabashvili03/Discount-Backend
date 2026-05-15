from django.db import models
from django.db.models import Value, FloatField, IntegerField
from staff.models import Company
from decimal import Decimal
from django.core.validators import MinValueValidator, MaxValueValidator, FileExtensionValidator
from services.models.category import Category
from services.models.city import City
from ..utils import image_upload, validate_image
from django.core.exceptions import ValidationError

def upload_service_image(instance, filename):
    return image_upload(instance, filename, 'service_images/')

def upload_service_video(instance, filename):
    return image_upload(instance, filename, 'service_videos/')


class EventQuerySet(models.QuerySet):
    def with_review_stats(self):
        # Annotates constants instead of joining services_eventreview so the
        # feed works without the reviews table existing.
        return self.annotate(
            avg_rating=Value(None, output_field=FloatField(null=True)),
            review_count=Value(0, output_field=IntegerField()),
            good_count=Value(0, output_field=IntegerField()),
            bad_count=Value(0, output_field=IntegerField()),
        )


class Event(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="events")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="events")
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="events")

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

    objects = EventQuerySet.as_manager()

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
    

class EventImage(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='images')
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
        return f"{self.event.name} | {self.alt_text} | {self.image}"


# Videos use FileField (not ImageField) so Pillow doesn't try to validate them.
# No size or duration cap — every upload is accepted. The extension allowlist
# keeps `.exe`/`.php`/`.html` from being stored under /uploads.
ALLOWED_VIDEO_EXTENSIONS = ['mp4', 'webm', 'mov', 'avi', 'mkv', 'm4v', 'ogv']


class EventVideo(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='videos')
    video = models.FileField(
        upload_to=upload_service_video,
        validators=[FileExtensionValidator(allowed_extensions=ALLOWED_VIDEO_EXTENSIONS)],
    )
    alt_text = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return f"{self.event.name} | {self.alt_text} | {self.video}"


class Discount(models.Model):
    DISCOUNT_TYPES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]
    
    service = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='discounts')
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
    


