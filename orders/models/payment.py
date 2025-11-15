from django.db import models
from orders.models import Order

PAYMENT_METHODS = [
    ('card', 'Credit/Debit Card'),
    ('bog_p2p', 'BoG P2P Transfer'),
    ('bog_loyalty', 'BoG Loyalty Points'),
    ('bog_loan', 'BoG Installments'),
    ('bnpl', 'Buy Now Pay Later'),
    ('google_pay', 'Google Pay'),
    ('apple_pay', 'Apple Pay'),
    ('gift_card', 'Gift Card'),
]

class Payment(models.Model):
    CAPTURE_TYPES = [
        ('automatic', 'Automatic'),
        ('manual', 'Manual'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('blocked', 'Blocked'),
        ('auth_requested', 'Authorization Requested'),
        ('partial_paid', 'Partial Paid'),
        ('refund_requested', 'Refund Requested'),
        ('refunded', 'Refunded'),
    ]

    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name='payment'
    )

    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0) 
    requested_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='GEL')

    transaction_id = models.CharField(max_length=100, blank=True)  
    capture_type = models.CharField(max_length=20, choices=CAPTURE_TYPES, default='manual')

    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending')

    method_provider = models.CharField(max_length=50, blank=True) 
    card_type = models.CharField(max_length=10, blank=True)       
    payer_identifier = models.CharField(max_length=200, blank=True)
    result_code = models.CharField(max_length=20, blank=True)     
    result_message = models.CharField(max_length=255, blank=True)  

    payment_gateway_response = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment for {self.order.order_number}"
