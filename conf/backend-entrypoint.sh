#!/usr/bin/env bash
set -e

if [[ "$1" = 'gunicorn' && "$RACK_ENV" != 'dev' ]]; then

    [ -f "$PROJECT_SECRETS_FILE" ] \
    || ( echo "Specify the secrets.json path in the env variable PROJECT_SECRETS_FILE" ; exit 1 )
    
    ./manage.py collectstatic --no-input \
    || ( n="$?" ; echo "Django fails to collectstatic: Exited $n" ; exit "$n" )

    ./manage.py check --deploy \
    || ( n="$?" ; echo "Check django settings for prod: Exited $n" ; exit "$n" )

    ./manage.py check --database default \
    || ( echo "Wait 30s for database ..." ; sleep 30 ; ./manage.py check --database default ) \
    || ( n="$?" ; echo "Django fails to check database: Exited $n" ; exit "$n" )

    ./manage.py makemigrations --no-input \
    || ( n="$?" ; echo "Django fails makemigrations: Exited $n" ; exit "$n" )

    ./manage.py migrate --no-input \
    || ( n="$?" ; echo "Django fails to migrate: Exited $n" ; exit "$n" )
    
    if [ -z "$GUNICORN_CMD_ARGS" ]; then
        export GUNICORN_CMD_ARGS="--workers=$(( $(nproc) * 2 + 1 )) --bind=0.0.0.0:8000 --access-logfile -"
    fi

fi

exec "$@"

