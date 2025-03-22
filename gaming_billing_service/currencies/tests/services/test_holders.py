from currencies.services import HoldersService
from django.test import TestCase


class HolderServicesTests(TestCase):
    def test_create_holder(self):
        holder = HoldersService.get_or_create(holder_id="test")
        self.assertEqual(holder.holder_id, "test")

    def test_double_create_holder(self):
        self.assertEqual(HoldersService.get_or_create(holder_id="test"), HoldersService.get_or_create(holder_id="test"))
