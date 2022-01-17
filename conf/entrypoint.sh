#!/usr/bin/env bash
set -e

if [ "$1" = 'gunicorn' ]; then
    chown -R "$USER" ./
    
    ./manage.py migrate --no-input \
    || ( n="$?" ; echo "Django fails to migrate: Exited $n" ; exit "$n" )

    ./manage.py collectstatic --no-input \
    || ( n="$?" ; echo "Django fails to collectstatic: Exited $n" ; exit "$n" )

    if [ -z "$GUNICORN_CMD_ARGS" ]; then
        export GUNICORN_CMD_ARGS="--workers=$(( $(nproc) * 2 + 1 )) --bind=127.0.0.1:8000"
    fi

fi

exec "$@"

