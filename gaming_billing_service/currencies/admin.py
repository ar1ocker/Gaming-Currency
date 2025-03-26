from django.contrib import admin
from django.http import HttpRequest

from .models import (
    AdjustmentTransaction,
    CheckingAccount,
    CurrencyUnit,
    ExchangeRule,
    ExchangeTransaction,
    Holder,
    HolderType,
    Service,
    TransferRule,
    TransferTransaction,
)


class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request: HttpRequest, obj=...):
        return False


@admin.register(TransferRule)
class TransferRuleAdmin(admin.ModelAdmin):
    list_display = [
        "enabled",
        "name",
        "unit",
        "fee_percent",
        "min_from_amount",
        "created_at",
        "updated_at",
    ]
    list_display_links = list_display
    list_filter = list_display


@admin.register(ExchangeRule)
class ExchangeRuleAdmin(admin.ModelAdmin):
    list_display = [
        "enabled_forward",
        "enabled_reverse",
        "first_unit",
        "second_unit",
        "forward_rate",
        "reverse_rate",
        "min_first_amount",
        "min_second_amount",
        "created_at",
        "updated_at",
    ]
    list_display_links = list_display
    list_filter = list_display


@admin.register(AdjustmentTransaction)
class AdjustmentTransactionAdmin(ReadOnlyAdmin):
    change_form_template = "adjustments/admin/change.html"
    change_list_template = "adjustments/admin/list.html"

    search_fields = [
        "uuid",
        "status_description",
        "service__name",
        "description__search",
        "checking_account__holder__holder_id",
    ]
    list_filter = ["status", "service", "created_at", "closed_at"]
    list_display = ["uuid", "service", "amount", "checking_account", "status", "created_at", "closed_at"]


@admin.register(TransferTransaction)
class TransferTransactionAdmin(ReadOnlyAdmin):
    change_form_template = "transfers/admin/change.html"
    change_list_template = "transfers/admin/list.html"

    search_fields = [
        "uuid",
        "status_description",
        "description",
        "from_checking_account__holder__holder_id",
        "to_checking_account__holder__holder_id",
        "service__name",
    ]
    list_filter = ["status", "service", "created_at", "closed_at"]
    list_display = [
        "uuid",
        "service__name",
        "from_amount",
        "to_amount",
        "from_checking_account",
        "to_checking_account",
        "status",
        "created_at",
        "closed_at",
    ]


@admin.register(ExchangeTransaction)
class ExchangeTransactionAdmin(ReadOnlyAdmin):
    change_form_template = "exchanges/admin/change.html"
    change_list_template = "exchanges/admin/list.html"

    search_fields = [
        "uuid",
        "status_description",
        "description",
        "from_checking_account__holder__holder_id",
        "to_checking_account__holder__holder_id",
        "service__name",
    ]
    list_filter = ["status", "service", "created_at", "closed_at"]
    list_display = [
        "uuid",
        "service__name",
        "from_amount",
        "to_amount",
        "from_checking_account",
        "to_checking_account",
        "status",
        "created_at",
        "closed_at",
    ]


@admin.register(CheckingAccount)
class CheckingAccountAdmin(admin.ModelAdmin):
    search_fields = ["holder"]
    list_filter = ["currency_unit", "created_at"]
    list_display = ["holder", "currency_unit__measurement", "amount", "created_at"]

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request: HttpRequest, obj=...):
        return False


@admin.register(CurrencyUnit)
class CurrencyUnitAdmin(admin.ModelAdmin):
    list_display = ["id", "symbol", "measurement"]


@admin.register(Holder)
class HolderAdmin(admin.ModelAdmin):
    list_display = ["holder_id", "holder_type", "enabled"]
    search_fields = ["holder_id", "holder_type"]

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request: HttpRequest, obj=...):
        return False


@admin.register(HolderType)
class HolderTypeAdmin(admin.ModelAdmin):
    list_display = ["name"]


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display: list[str] = ["name"]
