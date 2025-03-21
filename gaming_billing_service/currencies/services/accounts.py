from currencies.models import CheckingAccount, CurrencyUnit, Player


class AccountsService:
    @classmethod
    def get_or_create(cls, *, player: Player, currency_unit: CurrencyUnit) -> CheckingAccount:
        return CheckingAccount.objects.get_or_create(
            player=player, currency_unit=currency_unit, defaults={"amount": 0}
        )[0]
