import os
import sys
from datetime import timedelta
from decimal import ROUND_HALF_UP, getcontext
from pathlib import Path

import toml
from django.db.backends.postgresql.psycopg_any import IsolationLevel
from django.utils.safestring import mark_safe

# DECIMAL

getcontext().prec = 20
getcontext().rounding = ROUND_HALF_UP

# FOR TESTS

IS_LOCAL_RUN = bool(os.getenv("DJANGO_LOCAL_RUN"))
IS_TESTING = sys.argv[0].endswith("pytest")

# DJANGO BASE

BASE_DIR = Path(__file__).resolve().parent.parent

config = toml.load(BASE_DIR / "config.toml")

SECRET_KEY = config["DJANGO"]["SECRET_KEY"]

DEBUG = config["DJANGO"]["DEBUG"]

ALLOWED_HOSTS = config["DJANGO"]["ALLOWED_HOSTS"]

CSRF_TRUSTED_ORIGINS = config["DJANGO"]["CSRF_TRUSTED_ORIGINS"]

BASE_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "jazzmin",
    "django_celery_results",
    "django_celery_beat",
    "django_filters",
    "rest_framework",
]

DEBUG_MIDDLEWARE = []
DEBUG_APPS = []

if IS_TESTING:
    DEBUG_APPS = []
    DEBUG_MIDDLEWARE = []
elif DEBUG:
    DEBUG_APPS = ["debug_toolbar"]
    DEBUG_MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware"]


LOCAL_APPS = [
    "currencies",
    "currencies_api",
]

INSTALLED_APPS = [*THIRD_PARTY_APPS, *BASE_APPS, *DEBUG_APPS, *LOCAL_APPS]

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
        "DIRS": [BASE_DIR / "common" / "templates"],
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

if IS_LOCAL_RUN:
    print("[ ! ] Redefining the standard database to sqlite for local run, check settings/settings.py")

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
LOGIN_REDIRECT_URL = "/admin/"

# DJANGO SESSIONS

SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# DJANGO LOGGING

if not IS_TESTING:
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

LANGUAGE_CODE = "RU-ru"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

# DJANGO STATIC FILES

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "static"
STATICFILES_DIRS = [BASE_DIR / "common" / "static"]

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
HMAC_TIMESTAMP_HEADER = "X-SIGNATURE-TIMESTAMP"
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

# JAZZMIN

JAZZMIN_SETTINGS = {
    # title of the window (Will default to current_admin_site.site_title if absent or None)
    "site_title": "Gaming Currency",
    # Title on the login screen (19 chars max) (defaults to current_admin_site.site_header if absent or None)
    "site_header": "Gaming Currency",
    # Title on the brand (19 chars max) (defaults to current_admin_site.site_header if absent or None)
    "site_brand": "Gaming Currency",
    # Logo to use for your site, must be present in static files, used for brand on top left
    "site_logo": "logo/dollar.png",
    # Logo to use for your site, must be present in static files, used for login form logo (defaults to site_logo)
    "login_logo": None,
    # Logo to use for login form in dark themes (defaults to login_logo)
    "login_logo_dark": None,
    # CSS classes that are applied to the logo above
    "site_logo_classes": "img-circle",
    # Relative path to a favicon for your site, will default to site_logo if absent (ideally 32x32 px)
    "site_icon": None,
    # Welcome text on the login screen
    "welcome_sign": "Welcome to Gaming Currency",
    # Copyright on the footer
    "copyright": mark_safe('<a href="https://github.com/ar1ocker">github.com/ar1ocker</a>'),
    # List of model admins to search from the search bar, search bar omitted if excluded
    # If you want to use a single search field you dont need to use a list, you can use a simple string
    "search_model": "currencies.CheckingAccount",
    # Field name on user model that contains avatar ImageField/URLField/Charfield or a callable that receives the user
    "user_avatar": None,
    ############
    # Top Menu #
    ############
    # Links to put along the top menu
    "topmenu_links": [
        # App with dropdown menu to all its models pages (Permissions checked against models)
        {"app": "django_celery_beat"},
        {"app": "django_celery_results"},
    ],
    #############
    # Side Menu #
    #############
    # Whether to display the side menu
    "show_sidebar": True,
    # Whether to aut expand the menu
    "navigation_expanded": True,
    # Hide these apps when generating side menu e.g (auth)
    "hide_apps": ["django_celery_beat", "django_celery_results"],
    # List of apps (and/or models) to base side menu ordering off of (does not need to contain all apps/models)
    "order_with_respect_to": ["currencies", "currencies_api", "user"],
    # Custom icons for side menu apps/models See https://fontawesome.com/icons?d=gallery&m=free&v=5.0.0,5.0.1,5.0.10,5.0.11,5.0.12,5.0.13,5.0.2,5.0.3,5.0.4,5.0.5,5.0.6,5.0.7,5.0.8,5.0.9,5.1.0,5.1.1,5.2.0,5.3.0,5.3.1,5.4.0,5.4.1,5.4.2,5.13.0,5.12.0,5.11.2,5.11.1,5.10.0,5.9.0,5.8.2,5.8.1,5.7.2,5.7.1,5.7.0,5.6.3,5.5.0,5.4.2
    # for the full list of 5.13.0 free icon classes
    "icons": {
        "currencies.holder": "fas fa-user-tie",
        "currencies.currencyunit": "fas fa-money-bill",
        "currencies.exchangerule": "fas fa-exchange-alt",
        "currencies.transferrule": "fas fa-random",
        "currencies.currencyservice": "fas fa-hdd",
        "currencies.checkingaccount": "fas fa-file-invoice-dollar",
        "currencies.holdertype": "fas fa-question",
        "currencies.exchangetransaction": "fas fa-hands-wash",
        "currencies.transfertransaction": "fas fa-handshake",
        "currencies.adjustmenttransaction": "fas fa-hand-holding-usd",
        "currencies_api.currencyserviceauth": "fas fa-unlock",
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user",
        "auth.Group": "fas fa-users",
    },
}
