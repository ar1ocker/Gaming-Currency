from currencies.permissions import HoldersPermissionsService
from django.test import TestCase


class TestPermissionsClass(HoldersPermissionsService):
    verbose_name = "test_verbose"
    section_key = "test_section"


class HoldersPermissionTests(TestCase):
    def test_update_valid(self):
        permissions = {
            "test_section": {
                "enabled": True,
                "update": {
                    "enabled": True,
                },
            },
        }

        TestPermissionsClass.enforce_update(permissions=permissions)

    def test_update_disabled(self):
        permissions = {
            "test_section": {
                "enabled": True,
                "update": {
                    "enabled": False,
                },
            },
        }

        with self.assertRaisesMessage(TestPermissionsClass.PermissionDenied, "test_verbose: Update is disabled"):
            TestPermissionsClass.enforce_update(permissions=permissions)

    def test_section_disabled(self):
        permissions = {
            "test_section": {
                "enabled": False,
                "update": {
                    "enabled": True,
                },
            },
        }

        with self.assertRaisesMessage(TestPermissionsClass.PermissionDenied, "test_verbose: Access is disabled"):
            TestPermissionsClass.enforce_update(permissions=permissions)

    def test_root_is_true(self):
        permissions = {
            "root": True,
            "test_section": {
                "enabled": False,
                "update": {
                    "enabled": False,
                },
            },
        }

        TestPermissionsClass.enforce_update(permissions=permissions)
