from uuid import uuid1

from currencies.models import AdjustmentTransaction
from currencies.services import (
    AccountsService,
    AdjustmentsService,
    CurrencyServicesService,
)
from currencies.test_factories import CurrencyUnitsTestFactory, HoldersTestFactory
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.base import Message
from django.http import HttpResponse
from django.test import Client, TestCase
from django.urls import reverse

User = get_user_model()


class TransactionActionLoginTest(TestCase):
    def setUp(self) -> None:
        self.client = Client()

    def test_login_required_adjustment_create(self):
        response = self.client.get(reverse("currencies:adjustment_create"), follow=True)
        self.assertEqual(response.redirect_chain[0][1], 302, "Redirected unauthorized user to admin site")
        self.assertEqual(response.status_code, 200)

    def test_login_required_adjustment_confirm(self):
        response = self.client.get(reverse("currencies:adjustment_confirm", kwargs={"object_pk": 1}), follow=True)
        self.assertEqual(response.redirect_chain[0][1], 302, "Redirected unauthorized user to admin site")
        self.assertEqual(response.status_code, 200)

    def test_login_required_adjustment_reject(self):
        response: HttpResponse = self.client.get(
            reverse("currencies:adjustment_reject", kwargs={"object_pk": 1}), follow=True
        )
        self.assertEqual(response.redirect_chain[0][1], 302, "Redirected unauthorized user to admin site")
        self.assertEqual(response.status_code, 200)


class TransactionActionTest(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.uuid = uuid1()
        cls.superuser = User.objects.create_superuser("root", "email@example.com", "pass")
        cls.service = CurrencyServicesService.get_default()
        cls.holder = HoldersTestFactory()

        return super().setUpTestData()

    def assertMessages(self, response: HttpResponse, message: Message):
        msgs = list(messages.get_messages(response.wsgi_request))
        self.assertIn(message, msgs)

    def setUp(self) -> None:
        self.client.force_login(self.superuser)

        self.unit = CurrencyUnitsTestFactory()
        self.account = AccountsService.get_or_create(holder=self.holder, currency_unit=self.unit)

        self.transaction = AdjustmentsService.create(
            service=self.service, checking_account=self.account, amount=100, description="test description"
        )

    def send_confirm_request(self, object_pk: str) -> HttpResponse:
        return self.client.post(reverse("currencies:adjustment_confirm", kwargs={"object_pk": object_pk}), follow=True)

    def send_reject_request(self, object_pk: str) -> HttpResponse:
        return self.client.post(reverse("currencies:adjustment_reject", kwargs={"object_pk": object_pk}), follow=True)

    def test_adjustment_create_status_code(self):
        response = self.client.get(reverse("currencies:adjustment_create"))
        self.assertEqual(response.status_code, 200)

    def test_adjustment_create_post_view(self):
        count_transactions_before = AdjustmentTransaction.objects.count()
        response = self.client.post(
            reverse("currencies:adjustment_create"),
            {
                "service": self.service.pk,
                "holder_id": self.holder.holder_id,
                "to_unit": self.unit.pk,
                "amount": 100,
                "auto_reject_timedelta": 180,
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertMessages(response, Message(20, "Transaction created"))
        self.assertEqual(AdjustmentTransaction.objects.count(), count_transactions_before + 1)

    def test_adjustment_confirm(self):
        response = self.send_confirm_request(object_pk=str(self.transaction.uuid))
        self.assertEqual(response.status_code, 200)
        self.assertMessages(response, Message(20, "Transaction confirmed"))
        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.status, "CONFIRMED")

    def test_adjustment_reject(self):
        response = self.send_reject_request(object_pk=str(self.transaction.uuid))
        self.assertEqual(response.status_code, 200)
        self.assertMessages(response, Message(20, "Transaction rejected"))
        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.status, "REJECTED")

    def test_adjustment_confirm_double(self):
        self.send_confirm_request(object_pk=str(self.transaction.uuid))

        response = self.send_confirm_request(object_pk=str(self.transaction.uuid))
        self.assertEqual(response.status_code, 200)
        self.assertMessages(
            response, Message(40, "Error on confirm adjustment transaction The transaction has already been closed")
        )

    def test_adjustment_reject_double(self):
        self.send_reject_request(object_pk=str(self.transaction.uuid))

        response = self.send_reject_request(object_pk=str(self.transaction.uuid))
        self.assertEqual(response.status_code, 200)
        self.assertMessages(
            response, Message(40, "Error on reject adjustment transaction The transaction has already been closed")
        )

    def test_adjustment_reject_confirmed(self):
        self.send_confirm_request(object_pk=str(self.transaction.uuid))

        response = self.send_reject_request(object_pk=str(self.transaction.uuid))
        self.assertEqual(response.status_code, 200)
        self.assertMessages(
            response, Message(40, "Error on reject adjustment transaction The transaction has already been closed")
        )
        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.status, "CONFIRMED")

    def test_adjustment_confirm_rejected(self):
        self.send_reject_request(object_pk=str(self.transaction.uuid))

        response = self.send_confirm_request(object_pk=str(self.transaction.uuid))
        self.assertEqual(response.status_code, 200)
        self.assertMessages(
            response, Message(40, "Error on confirm adjustment transaction The transaction has already been closed")
        )
        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.status, "REJECTED")

    def test_adjustment_confirm_undefined(self):
        response = self.send_confirm_request(object_pk=str(self.uuid))

        self.assertEqual(response.status_code, 200)
        self.assertMessages(response, Message(40, "Adjustment transaction not found"))

    def test_adjustment_reject_undefined(self):
        response = self.send_reject_request(object_pk=str(self.uuid))

        self.assertEqual(response.status_code, 200)
        self.assertMessages(response, Message(40, "Adjustment transaction not found"))
