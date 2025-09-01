from django.db import models
from django.utils.translation import gettext_lazy as _
from .admin import Admin

class BlackList(models.Model):
    ip = models.GenericIPAddressField(unique=True)
    reason = models.TextField()
    created_by = models.ForeignKey(Admin, on_delete=models.CASCADE, related_name='black_lists')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Blacklist")
        verbose_name_plural = _("Blacklists")

    def __str__(self):
        return f"{self.ip} - {self.reason}"
    