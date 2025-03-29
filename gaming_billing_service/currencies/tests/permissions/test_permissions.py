from decimal import Decimal

from currencies.permissions import BasePermission
from django.test import TestCase


class TestPermissionsClass(BasePermission):
    verbose_name = "test_verbose"
    section_key = "test_section"


class PermissionAccessTests(TestCase):
    def test_access_valid(self):
        permissions = {"test_section": {"enabled": True}}

        TestPermissionsClass.enforce_access(permissions=permissions)

    def test_access_invalid_raise(self):
        permissions = {"test_section": {"enabled": False}}

        with self.assertRaisesMessage(TestPermissionsClass.PermissionDenied, "test_verbose: Access is disabled"):
            TestPermissionsClass.enforce_access(permissions=permissions)

    def test_access_empty_permissions_raise(self):
        permissions = {}

        with self.assertRaises(TestPermissionsClass.PermissionDenied):
            TestPermissionsClass.enforce_access(permissions=permissions)

    def test_access_valid_with_root_permissions(self):
        permissions = {"root": True}

        TestPermissionsClass.enforce_access(permissions=permissions)

    def test_access_invalid_with_root_false_permissions(self):
        permissions = {"root": False}

        with self.assertRaisesMessage(
            TestPermissionsClass.PermissionDenied, "test_verbose: Missing required permission 'test_section'"
        ):
            TestPermissionsClass.enforce_access(permissions=permissions)

    def test_access_invalid_with_root_trash_permissions(self):
        permissions = {"root": "random trash"}

        with self.assertRaisesMessage(
            TestPermissionsClass.PermissionDenied, "test_verbose: Missing required permission 'test_section'"
        ):
            TestPermissionsClass.enforce_access(permissions=permissions)

    def test_access_invalid_with_root_non_boolean_permissions(self):
        permissions = {"root": dict}

        with self.assertRaisesMessage(
            TestPermissionsClass.PermissionDenied, "test_verbose: Missing required permission 'test_section'"
        ):
            TestPermissionsClass.enforce_access(permissions=permissions)


class PermissionCreateTests(TestCase):
    def test_create_valid(self):
        permissions = {
            "test_section": {
                "enabled": True,
                "create": {
                    "enabled": True,
                },
            }
        }

        TestPermissionsClass.enforce_create(permissions=permissions)

    def test_create_disabled(self):
        permissions = {
            "test_section": {
                "enabled": True,
                "create": {
                    "enabled": False,
                },
            }
        }

        with self.assertRaisesMessage(TestPermissionsClass.PermissionDenied, "test_verbose: Creating is disabled"):
            TestPermissionsClass.enforce_create(permissions=permissions)

    def test_create_trash_in_permission(self):
        permissions = {
            "test_section": {
                "enabled": True,
                "create": {
                    "enabled": "some trash",
                },
            }
        }

        with self.assertRaisesMessage(TestPermissionsClass.PermissionDenied, "test_verbose: Creating is disabled"):
            TestPermissionsClass.enforce_create(permissions=permissions)

    def test_create_non_boolean_in_permission(self):
        permissions = {
            "test_section": {
                "enabled": True,
                "create": {
                    "enabled": {},
                },
            }
        }

        with self.assertRaisesMessage(TestPermissionsClass.PermissionDenied, "test_verbose: Creating is disabled"):
            TestPermissionsClass.enforce_create(permissions=permissions)

    def test_create_root_is_true(self):
        permissions = {
            "root": True,
            "test_section": {
                "enabled": True,
                "create": {
                    "enabled": False,
                },
            },
        }

        TestPermissionsClass.enforce_create(permissions=permissions)


class PermissionAmountTests(TestCase):
    def test_amount_valid(self):
        permissions = {
            "test_section": {
                "enabled": True,
                "create": {
                    "enabled": True,
                    "max_amount": 100,
                    "min_amount": 50,
                },
            }
        }

        TestPermissionsClass.enforce_amount(permissions=permissions, amount=Decimal("56.333"))

    def test_amount_invalid(self):
        permissions = {
            "test_section": {
                "enabled": True,
                "create": {
                    "enabled": True,
                    "max_amount": 55,
                    "min_amount": 50,
                },
            }
        }
        with self.assertRaisesMessage(TestPermissionsClass.PermissionDenied, "test_verbose: Amount is out of range"):
            TestPermissionsClass.enforce_amount(permissions=permissions, amount=Decimal("67.333"))

    def test_amount_trash_min_data(self):
        permissions = {
            "test_section": {
                "enabled": True,
                "create": {
                    "enabled": True,
                    "max_amount": 100,
                    "min_amount": "nnzixnczx",
                },
            }
        }

        with self.assertRaisesMessage(
            TestPermissionsClass.PermissionDenied, "test_verbose: Error in min_amount or in max_amount permission"
        ):
            TestPermissionsClass.enforce_amount(permissions=permissions, amount=Decimal("67.333"))

    def test_amount_trash_max_data(self):
        permissions = {
            "test_section": {
                "enabled": True,
                "create": {
                    "enabled": True,
                    "max_amount": {},
                    "min_amount": 10,
                },
            }
        }

        with self.assertRaisesMessage(
            TestPermissionsClass.PermissionDenied, "test_verbose: Error in min_amount or in max_amount permission"
        ):
            TestPermissionsClass.enforce_amount(permissions=permissions, amount=Decimal("67.333"))

    def test_amount_when_root_is_true(self):
        permissions = {
            "root": True,
            "test_section": {
                "enabled": False,
                "create": {
                    "enabled": False,
                    "max_amount": {},
                    "min_amount": "abrakadabra",
                },
            },
        }

        TestPermissionsClass.enforce_amount(permissions=permissions, amount=Decimal("99999999"))


class PermissionConfirmTests(TestCase):
    def test_confirm_valid(self):
        permissions = {
            "test_section": {
                "enabled": True,
                "confirm": {
                    "enabled": True,
                    "services": ["test_service"],
                },
            }
        }

        TestPermissionsClass.enforce_confirm(permissions=permissions, service_name="test_service")

    def test_confirm_not_found_service_in_list_raise(self):
        permissions = {
            "test_section": {
                "enabled": True,
                "confirm": {
                    "enabled": True,
                    "services": ["test_random_service"],
                },
            }
        }

        with self.assertRaisesMessage(
            TestPermissionsClass.PermissionDenied,
            "test_verbose: No access to confirm the transaction from another service",
        ):
            TestPermissionsClass.enforce_confirm(permissions=permissions, service_name="test_service")

    def test_confirm_not_found_service_key_raise(self):
        permissions = {
            "test_section": {
                "enabled": True,
                "confirm": {
                    "enabled": True,
                },
            }
        }

        with self.assertRaisesMessage(
            TestPermissionsClass.PermissionDenied,
            "test_verbose: Missing required permission 'services'",
        ):
            TestPermissionsClass.enforce_confirm(permissions=permissions, service_name="test_service")

    def test_confirm_disabled(self):
        permissions = {
            "test_section": {
                "enabled": True,
                "confirm": {
                    "enabled": False,
                    "services": ["test_service"],
                },
            }
        }

        with self.assertRaisesMessage(
            TestPermissionsClass.PermissionDenied,
            "test_verbose: Confirm is disabled",
        ):
            TestPermissionsClass.enforce_confirm(permissions=permissions, service_name="test_service")

    def test_confirm_when_root_is_true(self):
        permissions = {
            "root": True,
            "test_section": {
                "enabled": True,
                "confirm": {
                    "enabled": False,
                    "services": ["test_random_service"],
                },
            },
        }

        TestPermissionsClass.enforce_confirm(permissions=permissions, service_name="some_random")


class PermissionRejectTests(TestCase):
    def test_reject_valid(self):
        permissions = {
            "test_section": {
                "enabled": True,
                "reject": {
                    "enabled": True,
                    "services": ["test_service"],
                },
            }
        }

        TestPermissionsClass.enforce_reject(permissions=permissions, service_name="test_service")

    def test_reject_not_found_service_in_list_raise(self):
        permissions = {
            "test_section": {
                "enabled": True,
                "reject": {
                    "enabled": True,
                    "services": ["test_random_service"],
                },
            }
        }

        with self.assertRaisesMessage(
            TestPermissionsClass.PermissionDenied,
            "test_verbose: No access to reject the transaction from another service",
        ):
            TestPermissionsClass.enforce_reject(permissions=permissions, service_name="test_service")

    def test_reject_not_found_service_key_raise(self):
        permissions = {
            "test_section": {
                "enabled": True,
                "reject": {
                    "enabled": True,
                },
            }
        }

        with self.assertRaisesMessage(
            TestPermissionsClass.PermissionDenied,
            "test_verbose: Missing required permission 'services'",
        ):
            TestPermissionsClass.enforce_reject(permissions=permissions, service_name="test_service")

    def test_reject_disabled(self):
        permissions = {
            "test_section": {
                "enabled": True,
                "reject": {
                    "enabled": False,
                    "services": ["test_service"],
                },
            }
        }

        with self.assertRaisesMessage(
            TestPermissionsClass.PermissionDenied,
            "test_verbose: Reject is disabled",
        ):
            TestPermissionsClass.enforce_reject(permissions=permissions, service_name="test_service")

    def test_reject_when_root_is_true(self):
        permissions = {
            "root": True,
            "test_section": {
                "enabled": True,
                "reject": {
                    "enabled": False,
                    "services": ["test_random_service"],
                },
            },
        }

        TestPermissionsClass.enforce_reject(permissions=permissions, service_name="some_random")
