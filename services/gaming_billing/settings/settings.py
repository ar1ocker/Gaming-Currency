import sys
from datetime import timedelta
from decimal import ROUND_HALF_UP, getcontext
from pathlib import Path

import toml
from django.db.backends.postgresql.psycopg_any import IsolationLevel

# DECIMAL

getcontext().prec = 20
getcontext().rounding = ROUND_HALF_UP

# DJANGO BASE

BASE_DIR = Path(__file__).resolve().parent.parent

config = toml.load(BASE_DIR / "config.toml")

SECRET_KEY = config["DJANGO"]["SECRET_KEY"]

DEBUG = config["DJANGO"]["DEBUG"]

ALLOWED_HOSTS = config["DJANGO"]["ALLOWED_HOSTS"]

BASE_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "django_celery_results",
    "django_celery_beat",
    "django_filters",
    "rest_framework",
]

DEBUG_MIDDLEWARE = []
DEBUG_APPS = []

if "test" in sys.argv:
    DEBUG_APPS = []
    DEBUG_MIDDLEWARE = []
elif DEBUG:
    DEBUG_APPS = ["debug_toolbar"]
    DEBUG_MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware"]


LOCAL_APPS = [
    "currencies",
    "currencies_api",
]

INSTALLED_APPS = [*BASE_APPS, *DEBUG_APPS, *THIRD_PARTY_APPS, *LOCAL_APPS]

MIDDLEWARE = [
    *DEBUG_MIDDLEWARE,
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "settings.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "settings.wsgi.application"

# DJANGO DATABASE

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config["DJANGO"]["POSTGRES_DB"],
        "USER": config["DJANGO"]["POSTGRES_USER"],
        "PASSWORD": config["DJANGO"]["POSTGRES_PASSWORD"],
        "HOST": config["DJANGO"]["POSTGRES_HOST"],
        "PORT": config["DJANGO"]["POSTGRES_PORT"],
        "OPTIONS": {
            "isolation_level": IsolationLevel.SERIALIZABLE,
        },
    }
}

if "test" in sys.argv and "--no-input" not in sys.argv:
    print(
        "[ ! ] Redefining the standard database to sqlite for local testing, check settings/settings.py, "
        "add --no-input to disable redefining"
    )
    DATABASES["default"] = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }


# DJANGO AUTH

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LOGIN_URL = "/admin/login/"

# DJANGO SESSIONS

SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# DJANGO LOGGING

if "test" not in sys.argv:
    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "machine_readable": {
                "format": (
                    "{levelname} | {asctime} | {module} | {name} | {process:d} | "
                    "{thread:d} | {ip} | {status_code} | {message} | {params}"
                ),
                "style": "{",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "filters": {
            "add_ip": {
                "()": "common.logging_filters.AddIPFilter",
            },
            "add_request_params": {
                "()": "common.logging_filters.AddRequestParamsFilter",
            },
        },
        "handlers": {
            "console": {
                "level": "WARNING",
                "class": "logging.StreamHandler",
                "formatter": "machine_readable",
                "filters": ["add_ip", "add_request_params"],
            },
        },
        "root": {
            "handlers": ["console"],
            "level": "WARNING",
        },
    }

# DJANGO I18N

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

# DJANGO STATIC FILES

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "static"

# DJANGO ETC

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# DRF

REST_FRAMEWORK = {"EXCEPTION_HANDLER": "settings.exception_handlers.django_validation_error_exception_handler"}

# DEBUG TOOLBAR

DEBUG_TOOLBAR_CONFIG = {
    "SHOW_TOOLBAR_CALLBACK": lambda request: DEBUG,
    "PROFILER_MAX_DEPTH": 10,
}

# HMAC

ENABLE_HMAC_VALIDATION = config["HMAC"]["ENABLE"]
SERVICE_HEADER = "X-SERVICE"

BATTLEMETRICS_SIGNATURE_REGEX = r"(?<=s=)\w+(?=,|\Z)"
BATTLEMETRICS_TIMESTAMP_REGEX = r"(?<=t=)[\w\-:.+]+(?=,|\Z)"
HMAC_SIGNATURE_HEADER = "X-SIGNATURE"
HMAC_TIMESTAMP_HEADER = "X-SIGNATURE_TIMESTAMP"
HMAC_HASH_TYPE = "sha256"

HMAC_TIMESTAMP_DEVIATION = timedelta(seconds=config["HMAC"]["TIMESTAMP_DEVIATION"])


# Currency transactions

DEFAULT_AUTO_REJECT_TIMEDELTA = timedelta(seconds=config["CURRENCY_TRANSACTIONS"]["DEFAULT_AUTO_REJECT_SECONDS"])
DEFAULT_AUTO_REJECT_SECONDS = DEFAULT_AUTO_REJECT_TIMEDELTA.total_seconds()
CURRENCY_DEFAULT_HOLDER_TYPE_SLUG = "player"
ADMIN_SITE_SERVICE_NAME = "admin-site"

# CELERY

CELERY_RESULT_EXPIRES = timedelta(days=config["CELERY"]["RESULT_EXPIRES_DAYS"])
CELERY_BROKER_URL = config["CELERY"]["BROKER_URL"]
CELERY_RESULT_BACKEND = "django-db"
CELERY_RESULT_EXTENDED = True
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_WORKER_CONCURRENCY = 2
