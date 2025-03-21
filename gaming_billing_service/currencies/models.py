import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Service(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Сервис"
        verbose_name_plural = "Сервисы"


class Player(models.Model):
    player_id = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return f"Игрок {self.player_id}"

    class Meta:
        verbose_name = "Игрок"
        verbose_name_plural = "Игроки"


class CurrencyUnit(models.Model):
    symbol = models.CharField(max_length=10, unique=True)
    measurement = models.CharField(max_length=50)

    def __str__(self):
        return f"Игровая валюта {self.symbol}"

    class Meta:
        verbose_name = "Игровая валюта"
        verbose_name_plural = "Игровые валюты"


class ExchangeRule(models.Model):
    enabled_forward = models.BooleanField(default=False)
    enabled_reverse = models.BooleanField(default=False)

    first_unit = models.ForeignKey(CurrencyUnit, on_delete=models.CASCADE, related_name="first_exchanges")  # ПК
    second_unit = models.ForeignKey(CurrencyUnit, on_delete=models.CASCADE, related_name="second_exchanges")  # КК
    forward_rate = models.PositiveIntegerField()  # 100
    reverse_rate = models.PositiveIntegerField()  # 85
    min_first_amount = models.PositiveIntegerField()  # 100
    min_second_amount = models.PositiveIntegerField()  # 10
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Чтобы получить 200 КК нужно потратить forward_rate * 200 КК = 100 * 200 = 20 000 ПК
    # При трате 200 ПК мы получаем 200 ПК // forward_rate = 200 ПК // 100 = 2 КК
    # деление должно быть целочисленным и не иметь остатка, т.к. 200 ПК % forward_rate = 0

    # При трате 10 КК мы получаем reverse_rate * 10 КК = 85 * 10 КК = 850 ПК
    # Чтобы получить 850 ПК нужно потратить 850 ПК // reverse_rate = 850 ПК // 85 = 10
    # деление должно быть целочисленным и не иметь остатка, т.к. 850 КК % reverse_rate = 0

    @property
    def units(self):
        return (
            self.first_unit,
            self.second_unit,
        )

    def __str__(self):
        return f"{self.first_unit} по {self.forward_rate} за 1 {self.second_unit} / реверс {self.reverse_rate}"

    def clean(self):
        if self.first_unit == self.second_unit:
            raise ValidationError(
                {
                    "first_unit": "Валюты не могут быть одинаковыми",
                    "second_unit": "Валюты не могут быть одинаковыми",
                }
            )

    class Meta:
        verbose_name = "Правило обмена валюты"
        verbose_name_plural = "Правила обмена валют"

        constraints = [
            models.UniqueConstraint(fields=["first_unit", "second_unit"], name="unique_currency_unit_exchanges"),
        ]


class CheckingAccount(models.Model):
    player = models.ForeignKey(Player, on_delete=models.PROTECT, related_name="checking_accounts")
    currency_unit = models.ForeignKey(CurrencyUnit, on_delete=models.PROTECT)
    amount = models.PositiveBigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Счёт пользователя {self.player_id} - {self.amount}"  # type: ignore _id adds by django

    class Meta:
        verbose_name = "Счет пользователя"
        verbose_name_plural = "Счета пользователей"

        constraints = [
            models.UniqueConstraint(fields=["player", "currency_unit"], name="unique_user_currency"),
        ]


class BaseTransaction(models.Model):
    STATUSES = (("PENDING", "Pending"), ("CONFIRMED", "Confirmed"), ("REJECTED", "Rejected"))

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4)

    service = models.ForeignKey(Service, on_delete=models.PROTECT)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUSES, default="PENDING")
    status_description = models.TextField(blank=True)

    auto_reject_after = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    def _confirm(self, description: str):
        if self.status != "PENDING":
            raise ValidationError("The transaction has already been closed")

        self.status = "CONFIRMED"
        self.status_description = description
        self.closed_at = timezone.now()
        self.save()

    def _reject(self, description: str):
        if self.status != "PENDING":
            raise ValidationError("The transaction has already been closed")

        self.status = "REJECTED"
        self.status_description = description
        self.closed_at = timezone.now()
        self.save()

    class Meta:
        abstract = True


class CurrencyTransaction(BaseTransaction):
    checking_account = models.ForeignKey(CheckingAccount, on_delete=models.CASCADE, related_name="transactions")
    amount = models.BigIntegerField()

    def __str__(self):
        return (
            f"Транзакция {self.amount} на "  # type: ignore _id adds by django
            f"{self.checking_account_id} / {self.status}"  # type: ignore _id adds by django
        )

    class Meta:
        verbose_name = "Транзакция получения/вычета"
        verbose_name_plural = "Транзакции получения/вычета"


class TransferTransaction(BaseTransaction):
    from_checking_account = models.ForeignKey(CheckingAccount, on_delete=models.CASCADE, related_name="out_transfers")
    to_checking_account = models.ForeignKey(CheckingAccount, on_delete=models.CASCADE, related_name="in_transfers")
    amount = models.PositiveBigIntegerField()

    def __str__(self):
        return (
            f"Трансфер {self.amount} с {self.from_checking_account_id}"  # type: ignore _id adds by django
            f" на {self.to_checking_account_id} / {self.status}"  # type: ignore _id adds by django
        )

    class Meta:
        verbose_name = "Транзакция перевода"
        verbose_name_plural = "Транзакции перевода"


class ExchangeTransaction(BaseTransaction):
    exchange_rule = models.ForeignKey(ExchangeRule, on_delete=models.SET_NULL, null=True)

    from_checking_account = models.ForeignKey(
        CheckingAccount,
        on_delete=models.PROTECT,
        related_name="from_exchange_transactions",
    )
    to_checking_account = models.ForeignKey(
        CheckingAccount,
        on_delete=models.PROTECT,
        related_name="to_exchange_transactions",
    )

    from_amount = models.IntegerField()
    to_amount = models.IntegerField()

    def __str__(self):
        return "Обмен"

    class Meta:
        verbose_name = "Транзакция обмена"
        verbose_name_plural = "Транзакции обмена"
