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
            CheckingAccount.objects.get(holder=holder, currency_unit=currency_unit)
        except CheckingAccount.DoesNotExist:
            return None
