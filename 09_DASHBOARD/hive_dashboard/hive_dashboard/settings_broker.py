"""Minimal settings for broker_ops pipeline operations only."""
from hive_dashboard.settings import *  # noqa: F401,F403

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'business_os',
    'broker_ops',
]

ROOT_URLCONF = None

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
