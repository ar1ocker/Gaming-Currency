from django.contrib import admin

from .models import ServiceAuth


@admin.register(ServiceAuth)
class ServiceHMACAdmin(admin.ModelAdmin):
    list_display = ["service", "enabled", "is_battlemetrics"]
