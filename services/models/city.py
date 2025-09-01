from django.db import models
from services.models.country import Country

class City(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    population = models.IntegerField(blank=True, null=True)
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="cities", null=False, blank=False)

    class Meta:
        verbose_name_plural = "Cities"
    
    def __str__(self):
        return self.name
    


