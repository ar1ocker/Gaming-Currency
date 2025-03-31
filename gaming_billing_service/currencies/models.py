import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class CurrencyService(models.Model):
    name = models.SlugField(max_length=100, unique=True)
    enabled = models.BooleanField(default=False)
    permissions = models.JSONField(default=dict)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Сервис"
        verbose_name_plural = "Сервисы"


class HolderType(models.Model):
    name = models.SlugField(max_length=100, unique=True)

    def __str__(self):
        return f"Тип держателя {self.name}"

    class Meta:
        verbose_name = "Тип держателя"
        verbose_name_plural = "Типы держателей"

    @classmethod
    def get_default(cls):
        return cls.objects.get_or_create(name=settings.CURRENCY_DEFAULT_HOLDER_TYPE_SLUG)[0]

    @classmethod
    def get_default_holder_pk(cls):
        return cls.get_default().pk


class Holder(models.Model):
    enabled = models.BooleanField()
    holder_id = models.CharField(max_length=255, unique=True)
    holder_type = models.ForeignKey(
        HolderType,
        on_delete=models.PROTECT,
        related_name="holders",
    )
    info = models.JSONField(default=dict, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Держатель {self.holder_type}:{self.holder_id}"

    class Meta:
        verbose_name = "Держатель"
        verbose_name_plural = "Держатели"


class CurrencyUnit(models.Model):
    symbol = models.CharField(max_length=10, unique=True)
    measurement = models.CharField(max_length=50)

    def __str__(self):
        return f"Игровая валюта {self.symbol}"

    class Meta:
        verbose_name = "Игровая валюта"
        verbose_name_plural = "Игровые валюты"


class TransferRule(models.Model):
    enabled = models.BooleanField(default=False)

    name = models.CharField(max_length=255, unique=True)

    unit = models.ForeignKey(CurrencyUnit, on_delete=models.CASCADE)
    fee_percent = models.DecimalField(max_digits=6, decimal_places=1, validators=[MinValueValidator(0)])
    min_from_amount = models.DecimalField(max_digits=13, decimal_places=4, validators=[MinValueValidator(0)])

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Правило перевода валюты"
        verbose_name_plural = "Правила перевода валют"


class ExchangeRule(models.Model):
    enabled_forward = models.BooleanField(default=False)
    enabled_reverse = models.BooleanField(default=False)

    name = models.CharField(max_length=255, unique=True)

    first_unit = models.ForeignKey(CurrencyUnit, on_delete=models.CASCADE, related_name="first_exchanges")  # ПК
    second_unit = models.ForeignKey(CurrencyUnit, on_delete=models.CASCADE, related_name="second_exchanges")  # КК
    forward_rate = models.DecimalField(max_digits=13, decimal_places=4)  # 100
    reverse_rate = models.DecimalField(max_digits=13, decimal_places=4)  # 85
    min_first_amount = models.DecimalField(max_digits=13, decimal_places=4)  # 100
    min_second_amount = models.DecimalField(max_digits=13, decimal_places=4)  # 10
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
        return (
            f"{self.name} {self.first_unit} по {self.forward_rate} за 1 {self.second_unit} / реверс {self.reverse_rate}"
        )

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


class CheckingAccount(models.Model):
    holder = models.ForeignKey(Holder, on_delete=models.PROTECT, related_name="checking_accounts")
    currency_unit = models.ForeignKey(CurrencyUnit, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=13, decimal_places=4)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Счёт держателя {self.holder.holder_id} {self.currency_unit.symbol} - {self.amount}"

    class Meta:
        verbose_name = "Счет держателя"
        verbose_name_plural = "Счета держателей"

        constraints = [
            models.UniqueConstraint(fields=["holder", "currency_unit"], name="unique_holder_currency"),
        ]


class BaseTransaction(models.Model):
    STATUSES = (("PENDING", "Pending"), ("CONFIRMED", "Confirmed"), ("REJECTED", "Rejected"))

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4)

    service = models.ForeignKey(CurrencyService, on_delete=models.PROTECT)
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


class AdjustmentTransaction(BaseTransaction):
    checking_account = models.ForeignKey(CheckingAccount, on_delete=models.CASCADE, related_name="transactions")
    amount = models.DecimalField(max_digits=13, decimal_places=4)

    def __str__(self):
        return (
            f"Транзакция {self.amount} на "  # type: ignore _id adds by django
            f"{self.checking_account_id} / {self.status}"  # type: ignore _id adds by django
        )

    class Meta:
        verbose_name = "Транзакция получения/вычета"
        verbose_name_plural = "Транзакции получения/вычета"


class TransferTransaction(BaseTransaction):
    transfer_rule = models.ForeignKey(TransferRule, on_delete=models.SET_NULL, null=True)

    from_checking_account = models.ForeignKey(CheckingAccount, on_delete=models.CASCADE, related_name="out_transfers")
    to_checking_account = models.ForeignKey(CheckingAccount, on_delete=models.CASCADE, related_name="in_transfers")

    from_amount = models.DecimalField(max_digits=13, decimal_places=4, validators=[MinValueValidator(0)])
    to_amount = models.DecimalField(max_digits=13, decimal_places=4, validators=[MinValueValidator(0)])

    def __str__(self):
        return (
            f"Трансфер {self.from_amount} с {self.from_checking_account_id}"  # type: ignore _id adds by django
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

    from_amount = models.DecimalField(max_digits=13, decimal_places=4, validators=[MinValueValidator(0)])
    to_amount = models.DecimalField(max_digits=13, decimal_places=4, validators=[MinValueValidator(0)])

    def __str__(self):
        return "Обмен"

    class Meta:
        verbose_name = "Транзакция обмена"
        verbose_name_plural = "Транзакции обмена"
