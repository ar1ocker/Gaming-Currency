from django.contrib import admin

from .models import CurrencyServiceAuth


@admin.register(CurrencyServiceAuth)
class ServiceAuthAdmin(admin.ModelAdmin):
    list_display = ["service", "is_battlemetrics"]
