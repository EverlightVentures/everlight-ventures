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
    'blackjack',
    'rewards',
    'business_os',
    'broker_ops',
]

# -- Blackjack / Gaming --
GOOGLE_ADS_CLIENT = 'ca-pub-XXXXXXXXXXXXXXXX'   # Replace with real AdSense publisher ID
GOOGLE_ADS_SLOT_REWARD = ''                      # Replace with rewarded ad slot ID

# -- OAuth (Google + Facebook) --
# Set these in your shell environment before starting Django:
#   export GOOGLE_OAUTH_CLIENT_ID="...apps.googleusercontent.com"
#   export GOOGLE_OAUTH_CLIENT_SECRET="GOCSPX-..."
#   export FB_OAUTH_CLIENT_ID="..."
#   export FB_OAUTH_CLIENT_SECRET="..."
GOOGLE_OAUTH_CLIENT_ID = os.environ.get('GOOGLE_OAUTH_CLIENT_ID', '')
GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET', '')
FB_OAUTH_CLIENT_ID = os.environ.get('FB_OAUTH_CLIENT_ID', '')
FB_OAUTH_CLIENT_SECRET = os.environ.get('FB_OAUTH_CLIENT_SECRET', '')

# -- Session persistence (keeps login alive 30 days) --
SESSION_COOKIE_AGE = 60 * 60 * 24 * 30  # 30 days
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_SECURE = False  # Set True if HTTPS

# -- Monetization pricing tiers (documented for reference) --
# Chips (free): 1,000 signup bonus, 100/ad refill (10x/day), earned via play
# Gems (premium): $0.99 = 100 gems, $4.99 = 600 gems (+100 bonus), $9.99 = 1400 gems (+400)
# VIP: $4.99/mo (ad-free, 2x daily chips, exclusive cosmetics)
# Cosmetics: Common 500-2k chips / Rare 50-150 gems / Epic 150-300 gems / Legendary 300+ gems

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

# -- Email via Resend SMTP --
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('SMTP_HOST', 'smtp.resend.com')
EMAIL_PORT = int(os.environ.get('SMTP_PORT', '465'))
EMAIL_USE_SSL = True
EMAIL_USE_TLS = False
EMAIL_HOST_USER = os.environ.get('SMTP_USER', 'resend')
EMAIL_HOST_PASSWORD = os.environ.get('SMTP_PASS', '')
DEFAULT_FROM_EMAIL = os.environ.get('SMTP_FROM', 'noreply@everlightventures.io')
SERVER_EMAIL = DEFAULT_FROM_EMAIL

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
