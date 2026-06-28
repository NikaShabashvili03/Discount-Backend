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
    
    adult_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Optional adult price"
    )
    child_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Optional child price"
    )
    infant_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Optional infant price"
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

    TICKET_CHOICES = [
        ('per hour', 'per hour'),
        ('per day', 'per day'),
        ('per kilometer', 'per kilometer'),
        ('per room', 'per room'),
        ('per person', 'per person'),
        ('per car', 'per car'),
        ('per boat', 'per boat'),
        ('per driver', 'per driver'),
        ('per 10 minutes', 'per 10 minutes'),
        ('per 15 minutes', 'per 15 minutes'),
        ('per 30 minutes', 'per 30 minutes'),
        ('per loop', 'per loop'),
    ]
    event_ticket = models.CharField(
        max_length=50,
        choices=TICKET_CHOICES,
        null=True,
        blank=True,
        help_text="Optional ticket pricing/unit type"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = EventQuerySet.as_manager()

    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.id} | {self.name}"
    
    def calculate_price(self, people_count=None, adults_count=0, children_count=0, infants_count=0, age_prices_data=None, event_date=None):
        from datetime import datetime, time
        
        booking_time = None
        if event_date:
            if isinstance(event_date, str):
                try:
                    event_date = datetime.fromisoformat(event_date.replace('Z', '+00:00'))
                except ValueError:
                    pass
            if hasattr(event_date, 'time'):
                booking_time = event_date.time()
            elif isinstance(event_date, time):
                booking_time = event_date

        def matches_time(ap):
            if not ap.start_time or not ap.end_time:
                return True
            if booking_time is None:
                return True
            start = ap.start_time
            end = ap.end_time
            if start <= end:
                return start <= booking_time <= end
            return booking_time >= start or booking_time <= end

        # 1. Custom dynamic age-based pricing (preferred)
        if age_prices_data:
            total_price = Decimal('0.00')
            for item in age_prices_data:
                ap_id = item.get('age_price_id')
                qty = item.get('quantity', 0)
                if qty > 0:
                    try:
                        ap = self.age_prices.get(id=ap_id)
                        total_price += Decimal(str(ap.price)) * Decimal(str(qty))
                    except EventAgePrice.DoesNotExist:
                        pass
            return total_price

        # 2. If dynamic age prices exist, but only legacy counts were provided (fallback)
        if self.age_prices.exists() and (adults_count > 0 or children_count > 0 or infants_count > 0):
            total_price = Decimal('0.00')
            matching_aps = list(self.age_prices.all())
            if booking_time is not None:
                matching_aps = [ap for ap in matching_aps if matches_time(ap)]
            
            sorted_aps = sorted(matching_aps, key=lambda x: (x.min_age, x.start_time or time.min))
            
            infant_ap = next((ap for ap in sorted_aps if ap.max_age <= 2), None)
            child_ap = next((ap for ap in sorted_aps if 3 <= ap.min_age <= 12 or 3 <= ap.max_age <= 12), None)
            other_aps = [ap for ap in sorted_aps if ap != infant_ap and ap != child_ap]
            adult_ap = other_aps[-1] if other_aps else (sorted_aps[-1] if sorted_aps else None)
            
            if adult_ap and adults_count > 0:
                total_price += Decimal(str(adult_ap.price)) * Decimal(str(adults_count))
            if children_count > 0:
                cap = child_ap or adult_ap
                if cap:
                    total_price += Decimal(str(cap.price)) * Decimal(str(children_count))
            if infants_count > 0:
                iap = infant_ap or child_ap or adult_ap
                if iap:
                    total_price += Decimal(str(iap.price)) * Decimal(str(infants_count))
            return total_price

        # 3. Legacy age-specific pricing
        has_age_pricing = (self.child_price is not None) or (self.infant_price is not None)
        
        if has_age_pricing and (adults_count > 0 or children_count > 0 or infants_count > 0):
            # Calculate pricing based on age categories:
            adult_pr = self.adult_price if self.adult_price is not None else self.base_price
            child_pr = self.child_price if self.child_price is not None else adult_pr
            infant_pr = self.infant_price if self.infant_price is not None else adult_pr
            
            total_price = (Decimal(str(adults_count)) * Decimal(adult_pr)) + \
                          (Decimal(str(children_count)) * Decimal(child_pr)) + \
                          (Decimal(str(infants_count)) * Decimal(infant_pr))
            return total_price
        else:
            # Fall back to standard pricing
            if people_count is None:
                people_count = adults_count + children_count + infants_count
            if people_count < 1:
                people_count = 1
            total_price = self.base_price + (self.base_price * (people_count - 1))
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
    event = models.ForeignKey(Event, on_delete=models.DO_NOTHING, related_name='videos')
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


class EventAgePrice(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='age_prices')
    category_name = models.CharField(max_length=50, help_text="e.g. Toddler, Teenager, Senior, Student")
    min_age = models.IntegerField(validators=[MinValueValidator(0)])
    max_age = models.IntegerField(validators=[MinValueValidator(0)])
    price = models.DecimalField(max_digits=10, decimal_places=2)
    start_time = models.TimeField(null=True, blank=True, help_text="Applicable start time (for special type events)")
    end_time = models.TimeField(null=True, blank=True, help_text="Applicable end time (for special type events)")

    class Meta:
        ordering = ['min_age', 'start_time']

    def __str__(self):
        return f"{self.event.name} - {self.category_name} ({self.min_age}-{self.max_age}) [{self.start_time or ''}-{self.end_time or ''}]: ${self.price}"
    


