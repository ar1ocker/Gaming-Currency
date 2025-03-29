import decimal
from decimal import Decimal

from django.core.exceptions import PermissionDenied


class BasePermission:
    """
    Класс занимается проверкой переданных внутрь dict на наличие определенных параметров

    Пример
    {
        "root": False,  # Если True - остальные параметры не проверяются, предоставлены все возможные разрешения

        "section_name": {
            "enabled": True,  # Если False - остальные параметры внутри секции не проверяются, а enforce_access вызывает PermissionDenied
            "create": {
                "enabled": True,  # Если False - enforce_create вызывает PermissionDenied
                "min_amount": 100,  # Если переданный amount меньше минимального - вызывается PermissionDenied
                "max_amount": 200  # Если переданный amount больше максимального - вызывается PermissionDenied
            },
            "confirm": {
                "enabled": True,  # Если False - enforce_confirm вызывает PermissionDenied
                "services": ["service_1", "service_2"]  # Если переданный в enforce_confirm сервис не был найден в этом списке - вызывается PermissionDenied
            },
            "reject": {
                "enabled": True,  # Если False - enforce_reject вызывает PermissionDenied
                "services": ["service_1", "service_2"]  # Если переданный в enforce_reject сервис не был найден в этом списке - вызывается PermissionDenied
            }
        }
    }
    """  # noqa: E501

    PermissionDenied = PermissionDenied

    verbose_name: str = ""

    section_key: str = ""

    list_services_key: str = "services"

    root_key: str = "root"
    enabled_key: str = "enabled"

    create_key: str = "create"
    confirm_key: str = "confirm"
    reject_key: str = "reject"

    min_amount_key: str = "min_amount"
    max_amount_key: str = "max_amount"

    @classmethod
    def _is_root(cls, *, permissions: dict):
        try:
            return permissions[cls.root_key] is True
        except KeyError:
            return False

    @classmethod
    def _check_access(cls, *, permissions: dict):
        try:
            if permissions[cls.section_key][cls.enabled_key] is not True:
                raise PermissionDenied(f"{cls.verbose_name}: Access is disabled")
        except KeyError as e:
            raise PermissionDenied(f"{cls.verbose_name}: Missing required permission {e}")

    @classmethod
    def enforce_access(cls, *, permissions: dict):
        if cls._is_root(permissions=permissions):
            return

        cls._check_access(permissions=permissions)

    @classmethod
    def enforce_amount(cls, *, permissions: dict, amount: Decimal | int):
        if cls._is_root(permissions=permissions):
            return

        cls._check_access(permissions=permissions)

        try:
            create_section = permissions[cls.section_key][cls.create_key]

            max_amount = Decimal(create_section[cls.max_amount_key])
            min_amount = Decimal(create_section[cls.min_amount_key])

            if not (min_amount < amount < max_amount):
                raise PermissionDenied(f"{cls.verbose_name}: Amount is out of range")
        except KeyError as e:
            raise PermissionDenied(f"{cls.verbose_name}: Missing required permission {e}")
        except (TypeError, decimal.InvalidOperation):
            raise PermissionDenied(f"{cls.verbose_name}: Error in min_amount or in max_amount permission")

    @classmethod
    def enforce_create(cls, *, permissions: dict):
        if cls._is_root(permissions=permissions):
            return

        cls._check_access(permissions=permissions)

        try:
            create_section = permissions[cls.section_key][cls.create_key]

            if create_section[cls.enabled_key] is not True:
                raise PermissionDenied(f"{cls.verbose_name}: Creating is disabled")
        except KeyError as e:
            raise PermissionDenied(f"{cls.verbose_name}: Missing required permission {e}")

    @classmethod
    def enforce_confirm(cls, *, permissions: dict, service_name: str):
        if cls._is_root(permissions=permissions):
            return

        cls._check_access(permissions=permissions)

        try:
            confirm_section = permissions[cls.section_key][cls.confirm_key]

            if confirm_section[cls.enabled_key] is not True:
                raise PermissionDenied(f"{cls.verbose_name}: Confirm is disabled")

            if service_name not in confirm_section[cls.list_services_key]:
                raise PermissionDenied(f"{cls.verbose_name}: No access to confirm the transaction from another service")

        except KeyError as e:
            raise PermissionDenied(f"{cls.verbose_name}: Missing required permission {e}")

    @classmethod
    def enforce_reject(cls, *, permissions: dict, service_name: str):
        if cls._is_root(permissions=permissions):
            return

        cls._check_access(permissions=permissions)

        try:
            reject_section = permissions[cls.section_key][cls.reject_key]

            if reject_section[cls.enabled_key] is not True:
                raise PermissionDenied(f"{cls.verbose_name}: Reject is disabled")

            if service_name not in reject_section[cls.list_services_key]:
                raise PermissionDenied(f"{cls.verbose_name}: No access to reject the transaction from another service")

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
