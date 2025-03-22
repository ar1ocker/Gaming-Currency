from uuid import uuid1

from currencies.models import CurrencyUnit, ExchangeRule, ExchangeTransaction, Service
from currencies.services import (
    AccountsService,
    ExchangesService,
    HoldersService,
    HoldersTypeService,
    TransactionsService,
)
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.base import Message
from django.http import HttpResponse
from django.test import Client, TestCase
from django.urls import reverse

User = get_user_model()


class ExchangesActionLoginTests(TestCase):
    def setUp(self) -> None:
        self.client = Client()

    def test_login_required_exchanges_create(self):
        response = self.client.get(reverse("currencies:exchange_create"), follow=True)
        self.assertEqual(response.redirect_chain[0][1], 302, "Redirected unauthorized user to admin site")
        self.assertEqual(response.status_code, 200)

    def test_login_required_exchanges_confirm(self):
        response = self.client.get(reverse("currencies:exchange_confirm", kwargs={"object_pk": 1}), follow=True)
        self.assertEqual(response.redirect_chain[0][1], 302, "Redirected unauthorized user to admin site")
        self.assertEqual(response.status_code, 200)

    def test_login_required_exchanges_reject(self):
        response: HttpResponse = self.client.get(
            reverse("currencies:exchange_reject", kwargs={"object_pk": 1}), follow=True
        )
        self.assertEqual(response.redirect_chain[0][1], 302, "Redirected unauthorized user to admin site")
        self.assertEqual(response.status_code, 200)


class ExchangesActionTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.uuid = uuid1()
        cls.superuser = User.objects.create_superuser("root", "email@example.com", "pass")
        cls.service = Service.objects.create(name="test service")
        holder_type = HoldersTypeService.get_default()
        cls.holder = HoldersService.get_or_create(holder_id="holderidtest", holder_type=holder_type)
        cls.unit1 = CurrencyUnit.objects.create(symbol="ppg", measurement="popugi")
        cls.unit2 = CurrencyUnit.objects.create(symbol="uppg", measurement="ultra popugi")

        cls.checking_account1 = AccountsService.get_or_create(holder=cls.holder, currency_unit=cls.unit1)
        cls.checking_account2 = AccountsService.get_or_create(holder=cls.holder, currency_unit=cls.unit2)

        cls.rule = ExchangeRule.objects.create(
            enabled_forward=True,
            enabled_reverse=True,
            first_unit=cls.unit1,
            second_unit=cls.unit2,
            forward_rate=100,
            reverse_rate=100,
            min_first_amount=1,
            min_second_amount=1,
        )
        return super().setUpTestData()

    def setUp(self) -> None:
        self.client.force_login(self.superuser)
        TransactionsService.confirm(
            currency_transaction=TransactionsService.create(
                service=self.service, checking_account=self.checking_account1, amount=500, description=""
            ),
            status_description="",
        )

        TransactionsService.confirm(
            currency_transaction=TransactionsService.create(
                service=self.service, checking_account=self.checking_account2, amount=500, description=""
            ),
            status_description="",
        )

        self.transaction = ExchangesService.create(
            service=self.service,
            holder=self.holder,
            exchange_rule=self.rule,
            from_unit=self.unit1,
            to_unit=self.unit2,
            from_amount=100,
            description="",
        )

    def assertMessages(self, response: HttpResponse, message: Message):
        msgs = list(messages.get_messages(response.wsgi_request))
        self.assertIn(message, msgs)

    def send_confirm_request(self, object_pk: str) -> HttpResponse:
        return self.client.post(reverse("currencies:exchange_confirm", kwargs={"object_pk": object_pk}), follow=True)

    def send_reject_request(self, object_pk: str) -> HttpResponse:
        return self.client.post(reverse("currencies:exchange_reject", kwargs={"object_pk": object_pk}), follow=True)

    def test_exchange_create_status_code(self):
        response = self.client.get(reverse("currencies:exchange_create"))
        self.assertEqual(response.status_code, 200)

    def test_exchange_create_post_view(self):
        count_exchange_before = ExchangeTransaction.objects.count()
        response = self.client.post(
            reverse("currencies:exchange_create"),
            {
                "service": self.service.pk,
                "holder_id": self.holder.holder_id,
                "exchange_rule": self.rule.pk,
                "from_unit": self.unit1.pk,
                "to_unit": self.unit2.pk,
                "from_amount": 100,
                "auto_reject_timedelta": 180,
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertMessages(response, Message(20, "Transaction created"))
        self.assertEqual(ExchangeTransaction.objects.count(), count_exchange_before + 1)

    def test_exchange_confirm(self):
        response = self.send_confirm_request(object_pk=str(self.transaction.uuid))
        self.assertEqual(response.status_code, 200)
        self.assertMessages(response, Message(20, "Transaction confirmed"))
        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.status, "CONFIRMED")

    def test_exchange_reject(self):
        response = self.send_reject_request(object_pk=str(self.transaction.uuid))
        self.assertEqual(response.status_code, 200)
        self.assertMessages(response, Message(20, "Transaction rejected"))
        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.status, "REJECTED")

    def test_exchange_confirm_double(self):
        self.send_confirm_request(object_pk=str(self.transaction.uuid))

        response = self.send_confirm_request(object_pk=str(self.transaction.uuid))
        self.assertEqual(response.status_code, 200)
        self.assertMessages(
            response, Message(40, "Error on confirm exchange transaction The transaction has already been closed")
        )

    def test_exchange_reject_double(self):
        self.send_reject_request(object_pk=str(self.transaction.uuid))

        response = self.send_reject_request(object_pk=str(self.transaction.uuid))
        self.assertEqual(response.status_code, 200)
        self.assertMessages(
            response, Message(40, "Error on reject exchange transaction The transaction has already been closed")
        )

    def test_exchange_reject_confirmed(self):
        self.send_confirm_request(object_pk=str(self.transaction.uuid))

        response = self.send_reject_request(object_pk=str(self.transaction.uuid))
        self.assertEqual(response.status_code, 200)
        self.assertMessages(
            response, Message(40, "Error on reject exchange transaction The transaction has already been closed")
        )
        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.status, "CONFIRMED")

    def test_exchange_confirm_rejected(self):
        self.send_reject_request(object_pk=str(self.transaction.uuid))

        response = self.send_confirm_request(object_pk=str(self.transaction.uuid))
        self.assertEqual(response.status_code, 200)
        self.assertMessages(
            response, Message(40, "Error on confirm exchange transaction The transaction has already been closed")
        )
        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.status, "REJECTED")

    def test_exchange_confirm_undefined(self):
        response = self.send_confirm_request(object_pk=str(self.uuid))

        self.assertEqual(response.status_code, 200)
        self.assertMessages(response, Message(40, "Exchange transaction not found"))

    def test_exchange_reject_undefined(self):
        response = self.send_reject_request(object_pk=str(self.uuid))

        self.assertEqual(response.status_code, 200)
        self.assertMessages(response, Message(40, "Exchange transaction not found"))
