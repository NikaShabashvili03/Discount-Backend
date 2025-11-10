from panel.models.admin import Admin
from django.db import models
from services.utils import image_upload

def upload_slider_image(instance, filename):
    return image_upload(instance, filename, 'slider_images/')

class Slider(models.Model):
    admin = models.ForeignKey(Admin, on_delete=models.CASCADE)
    
    title = models.CharField(max_length=255)
    description = models.CharField(max_length=255)
    image = models.ImageField(upload_to=upload_slider_image)

    link = models.URLField(max_length=500, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
         return f"{self.title} | uploaded by {self.admin.firstname}"