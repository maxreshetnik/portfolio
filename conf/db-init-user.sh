#!/usr/bin/env bash

set -eau
    [ -f "${DB_ENV_FILE}" ] \
    || (echo "Environment variable file not found." ; exit 1) 
    . "${DB_ENV_FILE}"
set +a

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE USER ${PORTFOLIO_DB_USER}
    WITH PASSWORD '${PORTFOLIO_DB_PASSWORD}'
    NOSUPERUSER CREATEDB NOCREATEROLE;
    ALTER ROLE ${PORTFOLIO_DB_USER} SET client_encoding TO 'utf8';
    ALTER ROLE ${PORTFOLIO_DB_USER} SET default_transaction_isolation TO 'read committed';
    ALTER ROLE ${PORTFOLIO_DB_USER} SET timezone TO 'UTC';
    CREATE DATABASE ${PORTFOLIO_DB_USER};
    GRANT ALL PRIVILEGES ON DATABASE ${PORTFOLIO_DB_USER} TO ${PORTFOLIO_DB_USER};
EOSQL

unset PORTFOLIO_DB_PASSWORD POSTGRES_PASSWORD