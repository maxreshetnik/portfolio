from .common import *

DEBUG = True

ALLOWED_HOSTS = ['127.0.0.1', 'localhost'] + SECRETS.get('allowed_hosts', [])

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

CSRF_COOKIE_SECURE = False

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

LOGGING["loggers"]["django.db.backends"] = {
    'level': 'DEBUG',
    'handlers': ['console'],
    'propagate': False,
}

SESSION_COOKIE_SECURE = False

STATIC_ROOT = str(DATA_DIR.joinpath('static_dev'))
