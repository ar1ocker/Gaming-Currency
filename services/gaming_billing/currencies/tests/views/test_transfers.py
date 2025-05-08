from uuid import uuid1

from currencies.models import TransferRule, TransferTransaction
from currencies.services import (
    AccountsService,
    AdjustmentsService,
    CurrencyServicesService,
    TransfersService,
)
from currencies.test_factories import CurrencyUnitsTestFactory, HoldersTestFactory
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.base import Message
from django.http import HttpResponse
from django.test import Client, TestCase
from django.urls import reverse

User = get_user_model()


class TransferActionLoginTest(TestCase):
    def setUp(self) -> None:
        self.client = Client()

    def test_login_required_transfer_create(self):
        response = self.client.get(reverse("currencies:transfer_create"), follow=True)
        self.assertEqual(response.redirect_chain[0][1], 302, "Redirected unauthorized user to admin site")
        self.assertEqual(response.status_code, 200)

    def test_login_required_transfer_confirm(self):
        response = self.client.get(reverse("currencies:transfer_confirm", kwargs={"object_pk": 1}), follow=True)
        self.assertEqual(response.redirect_chain[0][1], 302, "Redirected unauthorized user to admin site")
        self.assertEqual(response.status_code, 200)

    def test_login_required_transfer_reject(self):
        response: HttpResponse = self.client.get(
            reverse("currencies:transfer_reject", kwargs={"object_pk": 1}), follow=True
        )
        self.assertEqual(response.redirect_chain[0][1], 302, "Redirected unauthorized user to admin site")
        self.assertEqual(response.status_code, 200)


class TransferActionTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.uuid = uuid1()
        cls.superuser = User.objects.create_superuser("root", "email@example.com", "pass")

        cls.service = CurrencyServicesService.get_default()
        cls.holder1 = HoldersTestFactory()
        cls.holder2 = HoldersTestFactory()
        cls.unit = CurrencyUnitsTestFactory()

        cls.transfer_rule = TransferRule(
            enabled=True, name="transferrule", unit=cls.unit, fee_percent=0, min_from_amount=1
        )
        cls.transfer_rule.full_clean()
        cls.transfer_rule.save()

    def assertMessages(self, response: HttpResponse, message: Message):
        msgs = list(messages.get_messages(response.wsgi_request))
        self.assertIn(message, msgs)

    def setUp(self) -> None:
        self.client.force_login(self.superuser)
        self.account1 = AccountsService.get_or_create(holder=self.holder1, currency_unit=self.unit)[0]

        AdjustmentsService.confirm(
            adjustment_transaction=AdjustmentsService.create(
                service=self.service, checking_account=self.account1, amount=200, description="test"
            ),
            status_description="teststatus",
        )

        account2 = AccountsService.get_or_create(holder=self.holder2, currency_unit=self.unit)[0]

        self.transfer = TransfersService.create(
            service=self.service,
            transfer_rule=self.transfer_rule,
            from_checking_account=self.account1,
            to_checking_account=account2,
            from_amount=100,
            description="test description",
        )

    def send_confirm_request(self, object_pk: str) -> HttpResponse:
        return self.client.post(reverse("currencies:transfer_confirm", kwargs={"object_pk": object_pk}), follow=True)

    def send_reject_request(self, object_pk: str) -> HttpResponse:
        return self.client.post(reverse("currencies:transfer_reject", kwargs={"object_pk": object_pk}), follow=True)

    def test_transaction_create_post_view(self):
        count_transactions_before = TransferTransaction.objects.count()
        response = self.client.post(
            reverse("currencies:transfer_create"),
            {
                "service": self.service.pk,
                "transfer_rule": self.transfer_rule.pk,
                "from_holder_id": self.holder1.holder_id,
                "to_holder_id": self.holder2.holder_id,
                "from_amount": 10,
                "auto_reject_timedelta": 180,
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertMessages(response, Message(20, "Transaction created"))
        self.assertEqual(TransferTransaction.objects.count(), count_transactions_before + 1)

    def test_transfer_confirm(self):
        response = self.send_confirm_request(object_pk=str(self.transfer.uuid))
        self.assertEqual(response.status_code, 200)
        self.assertMessages(response, Message(20, "Transfer transaction confirmed"))
        self.transfer.refresh_from_db()
        self.assertEqual(self.transfer.status, "CONFIRMED")

    def test_transfer_reject(self):
        response = self.send_reject_request(object_pk=str(self.transfer.uuid))
        self.assertEqual(response.status_code, 200)
        self.assertMessages(response, Message(20, "Transfer transaction rejected"))
        self.transfer.refresh_from_db()
        self.assertEqual(self.transfer.status, "REJECTED")

    def test_transfer_confirm_double(self):
        self.send_confirm_request(object_pk=str(self.transfer.uuid))

        response = self.send_confirm_request(object_pk=str(self.transfer.uuid))
        self.assertEqual(response.status_code, 200)
        self.assertMessages(
            response, Message(40, "Error on confirm transfer transaction The transaction has already been closed")
        )

    def test_transfer_reject_double(self):
        self.send_reject_request(object_pk=str(self.transfer.uuid))

        response = self.send_reject_request(object_pk=str(self.transfer.uuid))
        self.assertEqual(response.status_code, 200)
        self.assertMessages(
            response, Message(40, "Error on reject transfer transaction The transaction has already been closed")
        )

    def test_transfer_reject_confirmed(self):
        self.send_confirm_request(object_pk=str(self.transfer.uuid))

        response = self.send_reject_request(object_pk=str(self.transfer.uuid))
        self.assertEqual(response.status_code, 200)
        self.assertMessages(
            response, Message(40, "Error on reject transfer transaction The transaction has already been closed")
        )
        self.transfer.refresh_from_db()
        self.assertEqual(self.transfer.status, "CONFIRMED")

    def test_transfer_confirm_rejected(self):
        self.send_reject_request(object_pk=str(self.transfer.uuid))

        response = self.send_confirm_request(object_pk=str(self.transfer.uuid))
        self.assertEqual(response.status_code, 200)
        self.assertMessages(
            response, Message(40, "Error on confirm transfer transaction The transaction has already been closed")
        )
        self.transfer.refresh_from_db()
        self.assertEqual(self.transfer.status, "REJECTED")

    def test_transfer_confirm_undefined(self):
        response = self.send_confirm_request(object_pk=str(self.uuid))

        self.assertEqual(response.status_code, 200)
        self.assertMessages(response, Message(40, "Transfer transaction not found"))

    def test_transfer_reject_undefined(self):
        response = self.send_reject_request(object_pk=str(self.uuid))

        self.assertEqual(response.status_code, 200)
        self.assertMessages(response, Message(40, "Transfer transaction not found"))
