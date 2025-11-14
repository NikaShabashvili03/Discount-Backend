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

    # Payment basics
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # transfer_amount
    requested_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='GEL')

    # Transaction info from BOG
    transaction_id = models.CharField(max_length=100, blank=True)  
    capture_type = models.CharField(max_length=20, choices=CAPTURE_TYPES, default='manual')

    # Payment status from BOG
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending')

    # Extra BOG metadata
    method_provider = models.CharField(max_length=50, blank=True)  # BOG: card/google_pay/apple_pay/bog_p2p…
    card_type = models.CharField(max_length=10, blank=True)        # visa/mc/amex
    payer_identifier = models.CharField(max_length=200, blank=True) # masked card/account
    result_code = models.CharField(max_length=20, blank=True)      # BOG code: 100 = success
    result_message = models.CharField(max_length=255, blank=True)  # description

    # Save full raw callback/receipt JSON
    payment_gateway_response = models.JSONField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment for {self.order.order_number}"
