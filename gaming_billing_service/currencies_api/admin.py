from django.contrib import admin

from .models import ServiceHMAC


@admin.register(ServiceHMAC)
class ServiceHMACAdmin(admin.ModelAdmin):
    list_display = ["service", "enabled", "is_battlemetrics"]
