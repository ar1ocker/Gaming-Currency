from decimal import Decimal

from django.core.exceptions import PermissionDenied


class BasePermission:
    verbose_name: str = ""

    section_key: str = ""

    root_key: str = "root"
    enabled_key: str = "enabled"
    create_key: str = "create"
    min_amount_key: str = "min_amount"
    max_amount_key: str = "max_amount"

    @classmethod
    def _check_root(cls, *, permissions: dict):
        try:
            return permissions[cls.root_key] is True
        except KeyError:
            return False

    @classmethod
    def _check_access(cls, *, permissions: dict):
        try:
            return permissions[cls.section_key][cls.enabled_key] is True
        except KeyError:
            return False

    @classmethod
    def enforce_access(cls, *, permissions: dict):
        if cls._check_root(permissions=permissions):
            return

        if not cls._check_access(permissions=permissions):
            raise PermissionDenied(f"{cls.verbose_name}: Access is disabled")

    @classmethod
    def enforce_amount(cls, *, permissions: dict, amount: Decimal):
        cls.enforce_access(permissions=permissions)

        try:
            section = permissions[cls.section_key]

            max_amount = section[cls.max_amount_key]
            min_amount = section[cls.min_amount_key]

            if not (min_amount < amount < max_amount):
                raise PermissionDenied(f"{cls.verbose_name}: Amount is out of range")
        except KeyError as e:
            raise PermissionDenied(f"{cls.verbose_name}: Missing required permission {e}")

    @classmethod
    def enforce_create(cls, *, permissions: dict):
        cls.enforce_access(permissions=permissions)

        try:
            section = permissions[cls.section_key]

            if section[cls.create_key] is not True:
                raise PermissionDenied(f"{cls.verbose_name}: Creating is disabled")
        except KeyError as e:
            raise PermissionDenied(f"{cls.verbose_name}: Missing required permission {e}")


class AdjustmentsPermissionsService(BasePermission):
    verbose_name = "adjustments"
    section_key = "adjustments"


class ExchangesPermissionsService(BasePermission):
    verbose_name = "exchanges"
    section_key = "exchanges"


class TransfersPermissionsService(BasePermission):
    verbose_name = "transfers"
    section_key = "transfers"


class HoldersPermissionsService(BasePermission):
    verbose_name = "holders"
    section_key = "holders"


class AccountsPermissionsService(BasePermission):
    verbose_name = "accounts"
    section_key = "accounts"


class CurrencyUnitsPermissionsService(BasePermission):
    verbose_name = "currency units"
    section_key = "units"
