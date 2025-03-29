from currencies.models import CurrencyService
from django.db import models


class CurrencyServiceAuth(models.Model):
    service = models.OneToOneField(CurrencyService, on_delete=models.CASCADE, related_name="hmac")
    key = models.CharField(max_length=512)

    is_battlemetrics = models.BooleanField()

    def __str__(self):
        return f"Доступ сервиса '{self.service.name}'"

    class Meta:
        verbose_name = "Доступ сервиса"
        verbose_name_plural = "Доступ сервиса"
