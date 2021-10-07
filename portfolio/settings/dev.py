from .common import *

DEBUG = True

ALLOWED_HOSTS = []

CSRF_COOKIE_SECURE = False

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

MEDIA_ROOT = str(BASE_DIR.joinpath('media'))

SESSION_COOKIE_SECURE = False
