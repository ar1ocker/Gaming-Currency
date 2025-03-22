from currencies.models import CheckingAccount, CurrencyUnit, Holder


class AccountsService:
    @classmethod
    def get_or_create(cls, *, holder: Holder, currency_unit: CurrencyUnit) -> CheckingAccount:
        return CheckingAccount.objects.get_or_create(
            holder=holder, currency_unit=currency_unit, defaults={"amount": 0}
        )[0]
