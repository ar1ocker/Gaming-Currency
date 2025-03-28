import django_filters
from currencies.models import CheckingAccount, CurrencyUnit, Holder


class AccountsService:
    @classmethod
    def get_or_create(cls, *, holder: Holder, currency_unit: CurrencyUnit) -> CheckingAccount:
        return CheckingAccount.objects.get_or_create(
            holder=holder, currency_unit=currency_unit, defaults={"amount": 0}
        )[0]

    @classmethod
    def get(cls, *, holder: Holder, currency_unit: CurrencyUnit) -> CheckingAccount | None:
        try:
            return CheckingAccount.objects.get(holder=holder, currency_unit=currency_unit)
        except CheckingAccount.DoesNotExist:
            return None

    @classmethod
    def list(cls, *, filters=None):
        filters = filters or {}

        queryset = CheckingAccount.objects.all()

        return AccountsFilter(data=filters, queryset=queryset).qs


class AccountsFilter(django_filters.FilterSet):
    class Meta:
        model = CheckingAccount
        fields = (
            "holder",
            "currency_unit",
            "amount",
            "created_at",
        )
