"""
Hive Mind Dashboard - Django Settings
Everlight Ventures OS
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-7g)xhlbgyfm-(f@#8o9e8mm%=8xn%6(^-*jj-7h$l#x1(d@779'

DEBUG = True

ALLOWED_HOSTS = ['*']

# -- Hive data paths --
HIVE_SESSIONS_JSONL = os.environ.get(
    'HIVE_SESSIONS_JSONL',
    '/mnt/sdcard/AA_MY_DRIVE/_logs/hive_sessions.jsonl',
)
HIVE_WAR_ROOM_DIR = os.environ.get(
    'HIVE_WAR_ROOM_DIR',
    '/mnt/sdcard/AA_MY_DRIVE/_logs/ai_war_room',
)

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django_extensions',
    'django_htmx',
    'hive',
    'funnel',
    'taskboard',
    'payments',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
    'hive.middleware.RequestTimingMiddleware',
]

ROOT_URLCONF = 'hive_dashboard.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'hive.context_processors.hive_globals',
            ],
        },
    },
]

WSGI_APPLICATION = 'hive_dashboard.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'America/Los_Angeles'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

# -- Media / uploads --
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
FILE_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024   # 20 MB per file
DATA_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024    # 50 MB total (form + files)
HIVE_UPLOAD_DIR = '/mnt/sdcard/AA_MY_DRIVE/_uploads'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}
