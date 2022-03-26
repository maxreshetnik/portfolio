from .common import *


ADMINS = SECRETS.get('admins', [])

ALLOWED_HOSTS = SECRETS.get('allowed_hosts', [])

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': SECRETS.get('cache_location', '127.0.0.1:11211'),
        'OPTIONS': {
            'server_max_value_length': 1024 * 1024 * 2,
        }
    }
}

CSRF_COOKIE_SECURE = True

DEBUG = False

LOGGING["handlers"]["syslog"] = {
    "formatter": "full",
    "level": "DEBUG",
    "class": "logging.handlers.SysLogHandler",
    "address": "/dev/log",
    "facility": "local4",
}
LOGGING["loggers"]["django.request"]["handlers"].append("syslog")

SECURE_HSTS_INCLUDE_SUBDOMAINS = True

SECURE_HSTS_PRELOAD = True

SECURE_HSTS_SECONDS = 31536000

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

SECURE_SSL_REDIRECT = True

SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'

SESSION_COOKIE_SECURE = True

STATIC_ROOT = str(DATA_DIR.joinpath('static'))
