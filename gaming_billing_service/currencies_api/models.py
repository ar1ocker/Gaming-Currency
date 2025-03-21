from currencies.models import Service as CurrencyService
from django.db import models


class ServiceHMAC(models.Model):
    service = models.OneToOneField(CurrencyService, on_delete=models.CASCADE, related_name="hmac")
    enabled = models.BooleanField(default=False)
    key = models.CharField(max_length=512)

    is_battlemetrics = models.BooleanField()

    def __str__(self):
        return f"{self.service.name} HMAC key"

    class Meta:
        verbose_name = "HMAC сервиса"
        verbose_name_plural = "HMAC сервисов"
