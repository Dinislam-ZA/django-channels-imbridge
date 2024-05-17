from django.db import models


class Device(models.Model):
    device_id = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255, blank=True)
    image = models.JSONField(default=list)  # Двумерный список цветов 16x16
    brightness = models.IntegerField(default=100)
    is_on = models.BooleanField(default=True)
    is_connected = models.BooleanField(default=False)

    def __str__(self):
        return self.device_id
