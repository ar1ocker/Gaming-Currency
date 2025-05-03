from currencies.models import CurrencyService
from django.db import models


class CurrencyServiceAuth(models.Model):
    service = models.OneToOneField(
        verbose_name="Сервис", to=CurrencyService, on_delete=models.CASCADE, related_name="hmac"
    )
    key = models.CharField(verbose_name="Секретный ключ", max_length=512)

    is_battlemetrics = models.BooleanField(verbose_name="Сервис является Battlemetrics-ом")

    created_at = models.DateTimeField(verbose_name="Дата создания", auto_now_add=True)
    updated_at = models.DateTimeField(verbose_name="Дата обновления", auto_now=True)

    def __str__(self):
        return f"Доступ сервиса '{self.service.name}'"

    class Meta:
        verbose_name = "Доступ сервиса"
        verbose_name_plural = "Доступы сервисов"
