from currencies.models import Service as CurrencyService
from django.db import models


class ServiceAuth(models.Model):
    service = models.OneToOneField(CurrencyService, on_delete=models.CASCADE, related_name="hmac")
    enabled = models.BooleanField(default=False)
    key = models.CharField(max_length=512)

    is_battlemetrics = models.BooleanField()

    permissions = models.JSONField(default=dict)

    def __str__(self):
        return f"Доступ сервиса '{self.service.name}'"

    class Meta:
        verbose_name = "Доступ сервиса"
        verbose_name_plural = "Доступ сервиса"
