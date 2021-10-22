from .common import *


ADMINS = SECRETS.get('admins', [])

ALLOWED_HOSTS = ['127.0.0.1', 'localhost'] + SECRETS.get('allowed_hosts', [])

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
        'OPTIONS': {
            'server_max_value_length': 1024 * 1024 * 2,
        }
    }
}

CSRF_COOKIE_SECURE = True

DEBUG = False

SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'

SESSION_COOKIE_SECURE = True

STATIC_ROOT = str(DATA_DIR.joinpath('static'))

MEDIA_ROOT = str(DATA_DIR.joinpath('media'))
