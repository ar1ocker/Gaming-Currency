from typing import Any

import django_filters
from common.services import model_update
from currencies.models import Holder, HolderType
from django.db.models import QuerySet


class HoldersService:
    @classmethod
    def get_or_create(cls, *, holder_id: str, holder_type: HolderType, info: dict = {}) -> tuple[Holder, bool]:
        return Holder.objects.select_related("holder_type").get_or_create(
            holder_id=holder_id, defaults={"enabled": True, "holder_type": holder_type, "info": info}
        )

    @classmethod
    def get(cls, *, holder_id: str, holder_type: HolderType | None = None):
        try:
            if holder_type is None:
                return Holder.objects.select_related("holder_type").get(holder_id=holder_id)
            else:
                return Holder.objects.select_related("holder_type").get(holder_id=holder_id, holder_type=holder_type)
        except Holder.DoesNotExist:
            return None

    @classmethod
    def update(cls, *, holder: Holder, data: dict) -> tuple[Holder, bool]:
        fields = ["enabled", "info"]

        return model_update(instance=holder, fields=fields, data=data)

    @classmethod
    def list(cls, *, filters: dict[str, Any] | None = None) -> QuerySet[Holder]:
        filters = filters or {}

        queryset = Holder.objects.all()

        return HoldersFilter(data=filters, queryset=queryset).qs


class HoldersTypeService:
    @classmethod
    def get(cls, *, name: str):
        try:
            return HolderType.objects.get(name=name)
        except HolderType.DoesNotExist:
            return None

    @classmethod
    def get_default(cls):
        return HolderType.get_default()


class HoldersFilter(django_filters.FilterSet):
    enabled = django_filters.BooleanFilter()
    holder_id = django_filters.CharFilter()
    holder_type = django_filters.CharFilter(field_name="holder_type__name")
    created_at = django_filters.IsoDateTimeFromToRangeFilter()

    class Meta:
        model = Holder
        fields = ("enabled", "holder_id", "holder_type", "created_at")
