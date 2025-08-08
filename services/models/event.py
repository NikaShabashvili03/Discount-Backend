from django.db import models

class Event(models.Model):
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=100)
    description = models.CharField(max_length=100)
    category = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    durability = models.IntegerField()


    class Meta:
        verbose_name_plural = "Events"
    
    def __str__(self):
        return self.name
    
class Rating(models.Model):
    score = models.IntegerField()
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='rating')

    def __str__(self):
        return self.score
    
class KeyWord(models.Model):
    word = models.CharField(max_length=255)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='keywords')
    
    def __str__(self):
        return self.word