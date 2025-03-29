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

        with self.assertRaises(TestPermissionsClass.PermissionDenied):
            TestPermissionsClass.enforce_access(permissions=permissions)

    def test_access_invalid_with_root_trash_permissions(self):
        permissions = {"root": "random trash"}

        with self.assertRaises(TestPermissionsClass.PermissionDenied):
            TestPermissionsClass.enforce_access(permissions=permissions)

    def test_access_invalid_with_root_non_boolean_permissions(self):
        permissions = {"root": dict}

        with self.assertRaises(TestPermissionsClass.PermissionDenied):
            TestPermissionsClass.enforce_access(permissions=permissions)
