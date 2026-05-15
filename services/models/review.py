from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from customer.models import Customer
from services.models.event import Event


class EventReview(models.Model):
    MARK_CHOICES = [
        ('good', 'Good'),
        ('bad', 'Bad'),
        ('neutral', 'Neutral'),
    ]

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='reviews')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='reviews')

    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    mark = models.CharField(max_length=10, choices=MARK_CHOICES, default='neutral')
    title = models.CharField(max_length=200, blank=True)
    comment = models.TextField(blank=True)

    is_approved = models.BooleanField(default=True)
    is_flagged = models.BooleanField(default=False)
    flag_reason = models.CharField(max_length=255, blank=True)

    staff_reply = models.TextField(blank=True)
    staff_reply_at = models.DateTimeField(null=True, blank=True)

    helpful_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        # One review per customer per event. Re-submitting updates the existing
        # row instead of creating a duplicate.
        unique_together = ('event', 'customer')

    def __str__(self):
        return f"Review {self.id} | {self.event_id} | {self.rating}★"

    def save(self, *args, **kwargs):
        if self.rating >= 4:
            derived = 'good'
        elif self.rating <= 2:
            derived = 'bad'
        else:
            derived = 'neutral'
        if not self.mark or self.mark == 'neutral':
            self.mark = derived
        super().save(*args, **kwargs)


class EventReviewHelpful(models.Model):
    review = models.ForeignKey(EventReview, on_delete=models.CASCADE, related_name='helpful_votes')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='helpful_votes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('review', 'customer')

    def __str__(self):
        return f"Helpful {self.review_id} by {self.customer_id}"
