from typing import Any

from currencies.models import (
    AdjustmentTransaction,
    CheckingAccount,
    CurrencyService,
    CurrencyUnit,
    ExchangeRule,
    ExchangeTransaction,
    Holder,
    HolderType,
    TransferRule,
    TransferTransaction,
)
from django.contrib import admin
from django.db import models
from django.db.models.query import QuerySet
from django.http import HttpRequest


class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request: HttpRequest, obj=...):
        return False


@admin.register(TransferRule)
class TransferRuleAdmin(admin.ModelAdmin):
    fields = [
        "id",
        "enabled",
        "name",
        "unit",
        "fee_percent",
        "min_from_amount",
        "created_at",
        "updated_at",
    ]
    readonly_fields = ["id", "created_at", "updated_at"]
    list_display = [
        "id",
        "enabled",
        "name",
        "unit",
        "fee_percent",
        "min_from_amount",
        "created_at",
        "updated_at",
    ]
    list_display_links = list_display
    list_filter = [
        "enabled",
        "unit",
        "created_at",
        "updated_at",
    ]
    search_fields = ["name"]


@admin.register(ExchangeRule)
class ExchangeRuleAdmin(admin.ModelAdmin):
    fields = [
        "id",
        "enabled_forward",
        "enabled_reverse",
        "name",
        "first_unit",
        "second_unit",
        "forward_rate",
        "reverse_rate",
        "min_first_amount",
        "min_second_amount",
        "created_at",
        "updated_at",
    ]
    list_display = [
        "id",
        "enabled_forward",
        "enabled_reverse",
        "name",
        "first_unit",
        "second_unit",
        "forward_rate",
        "reverse_rate",
        "min_first_amount",
        "min_second_amount",
        "created_at",
        "updated_at",
    ]
    readonly_fields = ["id", "created_at", "updated_at"]
    list_display_links = list_display
    list_filter = ["enabled_forward", "enabled_reverse", "first_unit", "second_unit", "created_at", "updated_at"]
    search_fields = ["name"]


@admin.register(AdjustmentTransaction)
class AdjustmentTransactionAdmin(ReadOnlyAdmin):
    change_form_template = "adjustments/admin/change.html"
    change_list_template = "adjustments/admin/list.html"

    search_fields = [
        "uuid",
        "status_description",
        "service__name",
        "description",
        "checking_account__holder__holder_id",
    ]
    list_filter = ["status", "service", "created_at", "closed_at"]
    list_display = ["uuid", "service", "amount", "checking_account", "status", "created_at", "closed_at"]

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        return super().get_queryset(request).select_related("service", "checking_account")


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

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        return (
            super()
            .get_queryset(request)
            .select_related("service", "transfer_rule", "from_checking_account", "to_checking_account")
        )


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

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        return (
            super()
            .get_queryset(request)
            .select_related("service", "exchange_rule", "from_checking_account", "to_checking_account")
        )


@admin.register(CheckingAccount)
class CheckingAccountAdmin(admin.ModelAdmin):
    fields = ["id", "holder", "currency_unit", "amount", "created_at", "updated_at"]
    list_display = ["id", "holder", "currency_unit_measurement", "amount", "created_at", "updated_at"]
    list_display_links = list_display
    list_filter = ["currency_unit", "created_at", "updated_at"]
    readonly_fields = ["id", "created_at", "updated_at"]
    search_fields = ["holder__holder_id"]

    @admin.display(description="Валюта", ordering="currency_unit__measurement")
    def currency_unit_measurement(self, obj: CheckingAccount) -> str:
        return obj.currency_unit.measurement

    def has_delete_permission(self, request: HttpRequest, obj: CheckingAccount | None = None):
        return False

    def has_change_permission(self, request: HttpRequest, obj=...):
        return False


@admin.register(CurrencyUnit)
class CurrencyUnitAdmin(admin.ModelAdmin):
    fields = ["id", "symbol", "measurement", "precision", "is_negative_allowed", "created_at", "updated_at"]
    list_display = ["id", "symbol", "measurement", "precision"]
    list_display_links = list_display

    search_fields = ["symbol", "measurement"]
    list_filter = ["is_negative_allowed", "created_at", "updated_at"]
    readonly_fields = ["id", "created_at", "updated_at"]

    def get_deleted_objects(
        self, objs: QuerySet[CurrencyUnit], request: HttpRequest
    ) -> tuple[list[Any], dict[Any, Any], set[Any], list[Any]]:
        models.prefetch_related_objects(
            objs,
            "transfer_rules",
            "first_exchanges",
            "second_exchanges",
            "checking_accounts",
        )
        return super().get_deleted_objects(objs, request)


@admin.register(Holder)
class HolderAdmin(admin.ModelAdmin):
    fields = ["id", "enabled", "holder_id", "holder_type", "created_at", "updated_at"]
    list_display = ["id", "holder_id", "holder_type", "enabled", "created_at", "updated_at"]
    list_display_links = list_display
    search_fields = ["id", "holder_id", "holder_type__name"]
    readonly_fields = ["id", "holder_id", "holder_type", "created_at", "updated_at"]

    list_filter = ["created_at", "updated_at", "holder_type"]

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(HolderType)
class HolderTypeAdmin(admin.ModelAdmin):
    fields = ["id", "name", "created_at", "updated_at"]
    list_display = ["id", "name", "created_at", "updated_at"]
    list_display_links = list_display
    list_filter = ["created_at", "updated_at"]
    readonly_fields = ["id", "created_at", "updated_at"]
    search_fields = ["name"]


@admin.register(CurrencyService)
class ServiceAdmin(admin.ModelAdmin):
    fields = ["id", "enabled", "name", "permissions", "created_at", "updated_at"]
    list_display = ["id", "enabled", "name", "created_at", "updated_at"]
    list_display_links = list_display
    list_filter = ["enabled", "created_at", "updated_at"]
    readonly_fields = ["id", "created_at", "updated_at"]
    search_fields = ["name", "permissions"]
