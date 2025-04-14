import logging
from functools import wraps

from django.db import OperationalError
from decimal import Decimal

logger = logging.getLogger(__name__)


def retry_on_serialization_error(max_retries=3):
    """
    Декоратор для повторения вызова функции в случае ошибок сериализации.

    :param max_retries: Максимальное количество попыток.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except OperationalError as e:
                    # Проверяем, является ли ошибка ошибкой сериализации
                    if "serialization" in str(e).lower() or "could not serialize" in str(e).lower():
                        retries += 1
                        logger.warning(f"Ошибка сериализации (попытка {retries} из {max_retries}): {e}")
                        if retries >= max_retries:
                            logger.error("Достигнуто максимальное количество попыток сериализации.")
                            raise
                    else:
                        # Если это не ошибка сериализации, пробрасываем исключение дальше
                        raise

        return wrapper

    return decorator


def format_decimal(decimal: Decimal) -> str:
    s = format(decimal, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s
