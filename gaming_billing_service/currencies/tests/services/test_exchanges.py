from datetime import timedelta
from decimal import Decimal

from currencies.models import CurrencyService, ExchangeRule
from currencies.services import (
    AccountsService,
    AdjustmentsService,
    CurrencyServicesService,
    ExchangesService,
)
from currencies.test_factories import CurrencyUnitsTestFactory, HoldersTestFactory
from django.test import TestCase


class ExchangesServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.service = CurrencyServicesService.get_default()

        cls.holder = HoldersTestFactory()

        cls.unit1 = CurrencyUnitsTestFactory()
        cls.unit2 = CurrencyUnitsTestFactory()

        return super().setUpTestData()

    def setUp(self):
        self.checking_account_unit1 = AccountsService.get_or_create(holder=self.holder, currency_unit=self.unit1)
        self.checking_account_unit2 = AccountsService.get_or_create(holder=self.holder, currency_unit=self.unit2)

        self.exchange_rule = ExchangeRule.objects.create(
            name="test",
            enabled_forward=True,
            enabled_reverse=True,
            first_unit=self.unit1,
            second_unit=self.unit2,
            forward_rate=Decimal(10),
            reverse_rate=Decimal(5),
            min_first_amount=Decimal(20),
            min_second_amount=Decimal(10),
        )

        AdjustmentsService.confirm(
            adjustment_transaction=AdjustmentsService.create(
                service=self.service, checking_account=self.checking_account_unit1, amount=1000, description=""
            ),
            status_description="",
        )

        AdjustmentsService.confirm(
            adjustment_transaction=AdjustmentsService.create(
                service=self.service, checking_account=self.checking_account_unit2, amount=100, description=""
            ),
            status_description="",
        )

    def test_create_valid(self):
        exchange = ExchangesService.create(
            service=self.service,
            holder=self.holder,
            exchange_rule=self.exchange_rule,
            from_unit=self.unit1,
            to_unit=self.unit2,
            from_amount=100,
            description="",
        )

        self.assertEqual(exchange.service, self.service)
        self.assertEqual(exchange.from_checking_account.holder, self.holder)
        self.assertEqual(exchange.to_checking_account.holder, self.holder)
        self.assertEqual(exchange.from_checking_account.currency_unit, self.unit1)
        self.assertEqual(exchange.to_checking_account.currency_unit, self.unit2)
        self.assertEqual(exchange.from_amount, 100)
        self.assertEqual(exchange.to_amount, 10)

    def test_disabled_forward_raise_error(self):
        self.exchange_rule.enabled_forward = False
        self.exchange_rule.save()

        with self.assertRaisesMessage(ExchangesService.ValidationError, "Forward exchange is disabled"):
            ExchangesService.create(
                service=self.service,
                holder=self.holder,
                exchange_rule=self.exchange_rule,
                from_unit=self.unit1,
                to_unit=self.unit2,
                from_amount=100,
                description="",
            )

    def test_disabled_reverse_raise_error(self):
        self.exchange_rule.enabled_reverse = False
        self.exchange_rule.save()

        with self.assertRaisesMessage(ExchangesService.ValidationError, "Reverse exchange is disabled"):
            ExchangesService.create(
                service=self.service,
                holder=self.holder,
                exchange_rule=self.exchange_rule,
                from_unit=self.unit2,
                to_unit=self.unit1,
                from_amount=10,
                description="",
            )

    def test_with_not_included_units(self):
        new_unit = CurrencyUnitsTestFactory()
        with self.assertRaisesRegex(ExchangesService.ValidationError, ".*from_unit.*"):
            ExchangesService.create(
                service=self.service,
                holder=self.holder,
                exchange_rule=self.exchange_rule,
                from_unit=new_unit,
                to_unit=self.unit2,
                from_amount=1000,
                description="",
            )

        with self.assertRaisesRegex(ExchangesService.ValidationError, ".*to_unit.*"):
            ExchangesService.create(
                service=self.service,
                holder=self.holder,
                exchange_rule=self.exchange_rule,
                from_unit=self.unit1,
                to_unit=new_unit,
                from_amount=1000,
                description="",
            )

    def test_minimum_amount(self):
        with self.assertRaisesRegex(ExchangesService.ValidationError, ".*меньше минимальной.*"):
            ExchangesService.create(
                service=self.service,
                holder=self.holder,
                exchange_rule=self.exchange_rule,
                from_unit=self.unit1,
                to_unit=self.unit2,
                from_amount=1,
                description="",
            )

        with self.assertRaisesRegex(ExchangesService.ValidationError, ".*меньше минимальной.*"):
            ExchangesService.create(
                service=self.service,
                holder=self.holder,
                exchange_rule=self.exchange_rule,
                from_unit=self.unit2,
                to_unit=self.unit1,
                from_amount=1,
                description="",
            )

    def test_insufficient_amount(self):
        with self.assertRaisesRegex(ExchangesService.ValidationError, ".*Insufficient.*"):
            ExchangesService.create(
                service=self.service,
                holder=self.holder,
                exchange_rule=self.exchange_rule,
                from_unit=self.unit1,
                to_unit=self.unit2,
                from_amount=100000,
                description="",
            )

    def test_create_exchange_remove_amount_from_account(self):
        ExchangesService.create(
            service=self.service,
            holder=self.holder,
            exchange_rule=self.exchange_rule,
            from_unit=self.unit1,
            to_unit=self.unit2,
            from_amount=100,
            description="",
        )

        self.checking_account_unit1.refresh_from_db()
        self.assertEqual(self.checking_account_unit1.amount, 900)

    def test_confirm_exchange_change_status_and_status_description(self):
        exchange_transaction = ExchangesService.confirm(
            exchange_transaction=ExchangesService.create(
                service=self.service,
                holder=self.holder,
                exchange_rule=self.exchange_rule,
                from_unit=self.unit1,
                to_unit=self.unit2,
                from_amount=100,
                description="",
            ),
            status_description="test status description",
        )

        self.assertEqual(exchange_transaction.status_description, "test status description")
        self.assertEqual(exchange_transaction.status, "CONFIRMED")

    def test_reject_exchange_change_status_and_status_description(self):
        exchange_transaction = ExchangesService.reject(
            exchange_transaction=ExchangesService.create(
                service=self.service,
                holder=self.holder,
                exchange_rule=self.exchange_rule,
                from_unit=self.unit1,
                to_unit=self.unit2,
                from_amount=100,
                description="",
            ),
            status_description="test status description",
        )

        self.assertEqual(exchange_transaction.status_description, "test status description")
        self.assertEqual(exchange_transaction.status, "REJECTED")

    def test_confirm_exchange_add_amount_to_account_forward(self):
        ExchangesService.confirm(
            exchange_transaction=ExchangesService.create(
                service=self.service,
                holder=self.holder,
                exchange_rule=self.exchange_rule,
                from_unit=self.unit1,
                to_unit=self.unit2,
                from_amount=100,
                description="",
            ),
            status_description="test status description",
        )

        self.checking_account_unit2.refresh_from_db()

        # amount before transaction + from_amount // forward_rate
        self.assertEqual(self.checking_account_unit2.amount, 110)

    def test_confirm_exchange_add_amount_to_account_reverse(self):
        ExchangesService.confirm(
            exchange_transaction=ExchangesService.create(
                service=self.service,
                holder=self.holder,
                exchange_rule=self.exchange_rule,
                from_unit=self.unit2,
                to_unit=self.unit1,
                from_amount=100,
                description="",
            ),
            status_description="test status description",
        )

        self.checking_account_unit1.refresh_from_db()

        # amount before transaction + from_amount * reverse_rate
        self.assertEqual(self.checking_account_unit1.amount, 1500)

    def test_reject_exchange_returns_amount_to_from_amount_forward(self):
        ExchangesService.reject(
            exchange_transaction=ExchangesService.create(
                service=self.service,
                holder=self.holder,
                exchange_rule=self.exchange_rule,
                from_unit=self.unit1,
                to_unit=self.unit2,
                from_amount=100,
                description="",
            ),
            status_description="test status description",
        )

        self.checking_account_unit1.refresh_from_db()

        self.assertEqual(self.checking_account_unit1.amount, 1000)

    def test_reject_exchange_returns_amount_to_from_amount_reverse(self):
        ExchangesService.reject(
            exchange_transaction=ExchangesService.create(
                service=self.service,
                holder=self.holder,
                exchange_rule=self.exchange_rule,
                from_unit=self.unit2,
                to_unit=self.unit1,
                from_amount=100,
                description="",
            ),
            status_description="test status description",
        )

        self.checking_account_unit2.refresh_from_db()

        self.assertEqual(self.checking_account_unit2.amount, 100)

    def test_reject_outdated(self):
        exchange_transaction1 = ExchangesService.create(
            service=self.service,
            holder=self.holder,
            exchange_rule=self.exchange_rule,
            from_unit=self.unit1,
            to_unit=self.unit2,
            from_amount=100,
            description="",
            auto_reject_timedelta=timedelta(seconds=-1),
        )

        exchange_transaction2 = ExchangesService.create(
            service=self.service,
            holder=self.holder,
            exchange_rule=self.exchange_rule,
            from_unit=self.unit1,
            to_unit=self.unit2,
            from_amount=100,
            description="",
            auto_reject_timedelta=timedelta(seconds=-1),
        )

        rejecteds = ExchangesService.reject_all_outdated()
        self.assertEqual(len(rejecteds), 2)

        exchange_transaction1.refresh_from_db()
        exchange_transaction2.refresh_from_db()

        self.assertEqual(exchange_transaction1.status, "REJECTED")
        self.assertEqual(exchange_transaction2.status, "REJECTED")

    def test_validate_decimal_operations(self):
        exchange_rule = ExchangeRule.objects.create(
            name="test2",
            enabled_forward=True,
            enabled_reverse=True,
            first_unit=self.unit1,
            second_unit=self.unit2,
            forward_rate=Decimal("10.5"),
            reverse_rate=Decimal("5.3"),
            min_first_amount=Decimal(0),
            min_second_amount=Decimal(0),
        )

        exchange = ExchangesService.create(
            service=self.service,
            holder=self.holder,
            exchange_rule=exchange_rule,
            from_unit=self.unit1,
            to_unit=self.unit2,
            from_amount=Decimal("21"),
            description="",
        )

        self.assertEqual(exchange.to_amount, Decimal("2"))

        reverse_exchange = ExchangesService.create(
            service=self.service,
            holder=self.holder,
            exchange_rule=exchange_rule,
            from_unit=self.unit2,
            to_unit=self.unit1,
            from_amount=Decimal("2.35"),
            description="",
        )

        self.assertEqual(reverse_exchange.to_amount, Decimal("12.455"))

    def test_from_unit_precision_error(self):
        with self.assertRaisesRegex(
            ExchangesService.ValidationError, "Число знаков после запятой у снимаемой валюты больше чем возможно.*"
        ):
            ExchangesService.create(
                service=self.service,
                holder=self.holder,
                exchange_rule=self.exchange_rule,
                from_unit=self.unit1,
                to_unit=self.unit2,
                from_amount=Decimal("100.00000"),
                description="",
            )

    def test_to_unit_precision_error(self):
        exchange_rule = ExchangeRule.objects.create(
            name="test2",
            enabled_forward=True,
            enabled_reverse=True,
            first_unit=self.unit1,
            second_unit=self.unit2,
            forward_rate=Decimal("10.1"),
            reverse_rate=Decimal(5),
            min_first_amount=Decimal(20),
            min_second_amount=Decimal(10),
        )

        with self.assertRaisesRegex(
            ExchangesService.ValidationError, "Число знаков после запятой у получаемой валюты больше чем возможно.*"
        ):
            ExchangesService.create(
                service=self.service,
                holder=self.holder,
                exchange_rule=exchange_rule,
                from_unit=self.unit1,
                to_unit=self.unit2,
                from_amount=100,
                description="",
            )


class ExchangeServiceListTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.service_1 = CurrencyService.objects.create(name="service_test_1")
        cls.service_2 = CurrencyService.objects.create(name="service_test_2")

        cls.holder_1 = HoldersTestFactory()
        cls.holder_2 = HoldersTestFactory()

        cls.unit_1 = CurrencyUnitsTestFactory()
        cls.unit_2 = CurrencyUnitsTestFactory()

        cls.account_holder_1_unit_1 = AccountsService.get_or_create(holder=cls.holder_1, currency_unit=cls.unit_1)
        cls.account_holder_1_unit_2 = AccountsService.get_or_create(holder=cls.holder_1, currency_unit=cls.unit_2)
        cls.account_holder_2_unit_1 = AccountsService.get_or_create(holder=cls.holder_2, currency_unit=cls.unit_1)
        cls.account_holder_2_unit_2 = AccountsService.get_or_create(holder=cls.holder_2, currency_unit=cls.unit_2)

        cls.add_amount(
            accounts=(
                cls.account_holder_1_unit_1,
                cls.account_holder_1_unit_2,
                cls.account_holder_2_unit_1,
                cls.account_holder_2_unit_2,
            )
        )

        cls.exchange_rule = ExchangeRule.objects.create(
            enabled_forward=True,
            enabled_reverse=True,
            first_unit=cls.unit_1,
            second_unit=cls.unit_2,
            forward_rate=Decimal(10),
            reverse_rate=Decimal(5),
            min_first_amount=Decimal(1),
            min_second_amount=Decimal(1),
        )

        ExchangesService.create(
            service=cls.service_1,
            holder=cls.holder_1,
            exchange_rule=cls.exchange_rule,
            from_unit=cls.unit_1,
            to_unit=cls.unit_2,
            from_amount=10,
            description="exchange pending holder 1",
        )

        ExchangesService.create(
            service=cls.service_1,
            holder=cls.holder_2,
            exchange_rule=cls.exchange_rule,
            from_unit=cls.unit_1,
            to_unit=cls.unit_2,
            from_amount=10,
            description="exchange pending holder 2",
        )

        ExchangesService.confirm(
            exchange_transaction=ExchangesService.create(
                service=cls.service_1,
                holder=cls.holder_1,
                exchange_rule=cls.exchange_rule,
                from_unit=cls.unit_1,
                to_unit=cls.unit_2,
                from_amount=100,
                description="exchange confirmed holder 2",
            ),
            status_description="",
        )

        ExchangesService.confirm(
            exchange_transaction=ExchangesService.create(
                service=cls.service_1,
                holder=cls.holder_2,
                exchange_rule=cls.exchange_rule,
                from_unit=cls.unit_1,
                to_unit=cls.unit_2,
                from_amount=100,
                description="exchange confirmed holder 2",
            ),
            status_description="",
        )

        ExchangesService.reject(
            exchange_transaction=ExchangesService.create(
                service=cls.service_1,
                holder=cls.holder_1,
                exchange_rule=cls.exchange_rule,
                from_unit=cls.unit_2,
                to_unit=cls.unit_1,
                from_amount=300,
                description="exchange rejected",
            ),
            status_description="",
        )

        ExchangesService.reject(
            exchange_transaction=ExchangesService.create(
                service=cls.service_2,
                holder=cls.holder_1,
                exchange_rule=cls.exchange_rule,
                from_unit=cls.unit_2,
                to_unit=cls.unit_1,
                from_amount=300,
                description="exchange rejected service 2",
            ),
            status_description="",
        )

    @classmethod
    def add_amount(cls, *, accounts: list | tuple, amount=1000):
        for account in accounts:
            AdjustmentsService.confirm(
                adjustment_transaction=AdjustmentsService.create(
                    service=cls.service_1, checking_account=account, amount=amount, description=""
                ),
                status_description="",
            )

    def test_list_all(self):
        all_exchanges = ExchangesService.list()

        self.assertEqual(all_exchanges.count(), 6)

    def test_list_pending(self):
        pending_exchanges = ExchangesService.list(filters=dict(status="Pending"))

        self.assertEqual(pending_exchanges.count(), 2)

    def test_list_rejected(self):
        rejected_exchanges = ExchangesService.list(filters=dict(status="REJECTED"))

        self.assertEqual(rejected_exchanges.count(), 2)
        for exchange in rejected_exchanges:
            self.assertEqual(exchange.status, "REJECTED")

    def test_list_confirmed(self):
        confirmed_exchanges = ExchangesService.list(filters=dict(status="CONFIRMED"))

        self.assertEqual(confirmed_exchanges.count(), 2)
        for exchange in confirmed_exchanges:
            self.assertEqual(exchange.status, "CONFIRMED")

    def test_list_service_2(self):
        exchanges = ExchangesService.list(filters=dict(service="service_test_2"))

        self.assertEqual(exchanges.count(), 1)

        self.assertEqual(exchanges[0].service.name, "service_test_2")

    def test_list_holder_2(self):
        exchanges = ExchangesService.list(filters=dict(holder=self.holder_2.holder_id))

        self.assertEqual(exchanges.count(), 2)
        for exchange in exchanges:
            self.assertEqual(exchange.from_checking_account.holder.holder_id, self.holder_2.holder_id)
