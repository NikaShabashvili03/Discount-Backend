import secrets
import string

from django.db import models
from customer.models import Customer
from services.models import Event

# Excludes the visually-ambiguous 0/O/1/I so support staff can read order
# numbers aloud without confusion.
_ORDER_NUMBER_ALPHABET = ''.join(
    c for c in string.ascii_uppercase + string.digits if c not in '0O1I'
)


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    order_number = models.CharField(max_length=20, unique=True)

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='orders',
    )

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='orders')

    customer_name = models.CharField(max_length=200)
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=20)
    customer_country = models.CharField(max_length=100)

    people_count = models.IntegerField()
    event_date = models.DateTimeField()
    notes = models.TextField(blank=True)

    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order {self.order_number} - {self.event.name}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)

    @staticmethod
    def generate_order_number():
        # Cryptographically random + uniqueness retry. Old impl used
        # random.choices() (Mersenne Twister, predictable) and no retry, which
        # both made order numbers guessable and risked IntegrityError on collision.
        for _ in range(10):
            candidate = ''.join(secrets.choice(_ORDER_NUMBER_ALPHABET) for _ in range(10))
            if not Order.objects.filter(order_number=candidate).exists():
                return candidate
        raise RuntimeError("Could not allocate a unique order_number after 10 attempts.")