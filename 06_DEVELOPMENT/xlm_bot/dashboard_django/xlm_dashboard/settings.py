"""Django settings for XLM Trading Dashboard."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
XLM_BOT_DIR = Path(os.environ.get("XLM_BOT_DIR", str(BASE_DIR.parent)))

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-xlm-dashboard-insecure-change-in-prod")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = ["*"]

# -- XLM Bot data paths --
XLM_DATA_DIR = Path(os.environ.get("XLM_DASH_DATA_DIR", str(XLM_BOT_DIR / "data")))
XLM_LOGS_DIR = Path(os.environ.get("XLM_DASH_LOGS_DIR", str(XLM_BOT_DIR / "logs")))
XLM_EXCHANGE_READ = os.environ.get("XLM_DASH_EXCHANGE_READ", "1") == "1"
XLM_WORKSPACE_ROOT = Path(os.environ.get("WORKSPACE_ROOT", "/mnt/sdcard/AA_MY_DRIVE"))

# Coinbase config path
_vendor = XLM_BOT_DIR / "vendor"
_default_cb = str(_vendor / "config.json") if _vendor.is_dir() else str(XLM_BOT_DIR / "config.json")
XLM_COINBASE_CONFIG = Path(os.environ.get("COINBASE_CONFIG_PATH", _default_cb))

# Dashboard tuning
XLM_HISTORY_DAYS = int(os.environ.get("XLM_DASH_HISTORY_DAYS", "7"))
XLM_HISTORY_MAX_LINES = int(os.environ.get("XLM_DASH_HISTORY_MAX_LINES", "120000"))
XLM_HISTORY_MAX_MB = int(os.environ.get("XLM_DASH_HISTORY_MAX_MB", "24"))
XLM_CHAT_URL = os.environ.get("XLM_CHAT_URL", "http://127.0.0.1:8504/launch/")

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "django_htmx",
    "trading",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "trading.middleware.RequestTimingMiddleware",
]

ROOT_URLCONF = "xlm_dashboard.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.template.context_processors.static",
                "trading.context_processors.trading_globals",
            ],
        },
    },
]

WSGI_APPLICATION = "xlm_dashboard.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "TIMEOUT": 60,
    }
}

TIME_ZONE = "America/Los_Angeles"
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
