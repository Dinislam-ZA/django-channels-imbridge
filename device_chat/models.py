from django.db import models
from django.contrib.auth.models import User


class Device(models.Model):
    device_id = models.CharField(max_length=100, unique=True)
    image = models.JSONField(default=list)  # Двумерный список цветов 16x16
    brightness = models.IntegerField(default=100)
    is_on = models.BooleanField(default=True)

    def __str__(self):
        return self.device_id
