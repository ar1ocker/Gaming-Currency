import django_filters
from currencies.models import CheckingAccount, CurrencyUnit, Holder


class AccountsService:
    @classmethod
    def get_or_create(cls, *, holder: Holder, currency_unit: CurrencyUnit) -> CheckingAccount:
        return CheckingAccount.objects.select_related("currency_unit").get_or_create(
            holder=holder, currency_unit=currency_unit, defaults={"amount": 0}
        )[0]

    @classmethod
    def get(cls, *, holder: Holder, currency_unit: CurrencyUnit) -> CheckingAccount | None:
        try:
            return CheckingAccount.objects.select_related("currency_unit").get(
                holder=holder, currency_unit=currency_unit
            )
        except CheckingAccount.DoesNotExist:
            return None

    @classmethod
    def list(cls, *, filters: dict[str, str] | None = None):
        filters = filters or {}

        queryset = CheckingAccount.objects.all()

        return AccountsFilter(data=filters, queryset=queryset).qs


class AccountsFilter(django_filters.FilterSet):
    holder_type = django_filters.CharFilter(field_name="holder__holder_type__name")
    holder_id = django_filters.CharFilter(field_name="holder__holder_id")
    currency_unit = django_filters.CharFilter(field_name="currency_unit__symbol")
    amount = django_filters.RangeFilter()
    created_at = django_filters.IsoDateTimeFromToRangeFilter()

    class Meta:
        model = CheckingAccount
        fields = (
            "holder",
            "currency_unit",
            "amount",
            "created_at",
        )
