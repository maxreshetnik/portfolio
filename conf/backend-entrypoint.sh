#!/usr/bin/env bash
set -e

echo -e "\nRunning $0"
if [ "$RACK_ENV" != 'dev' ]; then

    [ -f "$PROJECT_SECRETS_FILE" ] \
    || ( echo "Specify the secrets.json path in the env variable PROJECT_SECRETS_FILE" ; exit 1 )
    
    echo -e "\nCollect static files"
    ./manage.py collectstatic --no-input

    echo "Check default database"
    ./manage.py check --database default || sleep 30 && ./manage.py check --database default

    echo -e "\nCheck django settings: ${DJANGO_SETTINGS_MODULE}"
    ./manage.py check --deploy

    ./manage.py makemigrations --no-input \
    || ( n="$?" ; echo "Django fails makemigrations: Exited $n" ; exit "$n" )

    ./manage.py migrate --no-input \
    || ( n="$?" ; echo "Django fails to migrate: Exited $n" ; exit "$n" )
fi
    
if [ "$1" = 'gunicorn' ] && [ -z "$GUNICORN_CMD_ARGS" ]; then
    w="--workers=$(( $(nproc) * 2 + 1 ))" 
    b="--bind=0.0.0.0:8000" 
    log="--access-logfile -"
    echo -e "\nStarting gunicorn with args: $w $b $log \n"
    exec gunicorn $w $b $log ${!#}
else
    exec "$@"
fi
