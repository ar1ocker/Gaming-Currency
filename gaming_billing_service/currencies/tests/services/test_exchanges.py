from datetime import timedelta

from currencies.models import CurrencyService, CurrencyUnit, ExchangeRule
from currencies.services import (
    AccountsService,
    AdjustmentsService,
    ExchangesService,
    HoldersService,
    HoldersTypeService,
)
from django.test import TestCase


class ExchangesServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.service = CurrencyService.objects.create(name="service_name")

        holder_type = HoldersTypeService.get_default()
        cls.holder = HoldersService.get_or_create(holder_id="testholderid", holder_type=holder_type)

        cls.unit1 = CurrencyUnit.objects.create(symbol="ppg", measurement="попугаи")
        cls.unit2 = CurrencyUnit.objects.create(symbol="ultrappg", measurement="ультра попугаи")

        return super().setUpTestData()

    def setUp(self):
        self.checking_account_unit1 = AccountsService.get_or_create(holder=self.holder, currency_unit=self.unit1)
        self.checking_account_unit2 = AccountsService.get_or_create(holder=self.holder, currency_unit=self.unit2)

        self.exchange_rule = ExchangeRule.objects.create(
            enabled_forward=True,
            enabled_reverse=True,
            first_unit=self.unit1,
            second_unit=self.unit2,
            forward_rate=10,
            reverse_rate=5,
            min_first_amount=20,
            min_second_amount=10,
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

    def test_disabled_reverse_transaction_raise_error(self):
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
        new_unit = CurrencyUnit.objects.create(symbol="newunit", measurement="newmeasurement")
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

    def test_not_integer_division(self):
        with self.assertRaisesRegex(ExchangesService.ValidationError, ".*не делится нацело.*"):
            ExchangesService.create(
                service=self.service,
                holder=self.holder,
                exchange_rule=self.exchange_rule,
                from_unit=self.unit1,
                to_unit=self.unit2,
                from_amount=35,
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
