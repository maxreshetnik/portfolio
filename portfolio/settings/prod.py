from .common import *


ALLOWED_HOSTS = ['127.0.0.1', 'localhost'] + SECRETS.get('allowed_hosts', [])

CSRF_COOKIE_SECURE = True

DEBUG = False

SESSION_COOKIE_SECURE = True

STATIC_ROOT = str(DATA_DIR.joinpath('static'))

MEDIA_ROOT = str(DATA_DIR.joinpath('media'))
