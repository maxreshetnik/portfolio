from .common import *

DEBUG = True

ALLOWED_HOSTS = ['127.0.0.1', 'localhost']

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

CSRF_COOKIE_SECURE = False

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

SESSION_COOKIE_SECURE = False
