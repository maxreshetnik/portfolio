#!/bin/sh

set -eu

openssl version || return 0

SSL_CRT_FILE="${SSL_DIR}/live/${DOMAIN_NAME}/fullchain.pem"
SSL_KEY_FILE="${SSL_DIR}/live/${DOMAIN_NAME}/privkey.pem"
SSL_DHPARAM="${SSL_DIR}/ssl-dhparams.pem"
SSL_OPTS_FILE="${SSL_DIR}/options-ssl-nginx.conf"
SSL_WEBROOT="${SSL_DIR}/html"

set +u

if [ ! -f "${SSL_DHPARAM}" ]; then
    openssl dhparam -out "${SSL_DHPARAM}" 2048 \
    || ( echo "Openssl fails to create dhparam.pem: Exited $?" ; exit 1 )
fi

if [ ! -f "${SSL_KEY_FILE}" ] || [ ! -f "${SSL_CRT_FILE}" ]; then
    mkdir -p "$(dirname ${SSL_KEY_FILE})"
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -subj "/C=XX/CN=${DOMAIN_NAME}" \
    -keyout "${SSL_KEY_FILE}" -out "${SSL_CRT_FILE}" \
    || echo "Openssl fails to create key or cert: Exited $?"
fi

if [ ! -f "${SSL_OPTS_FILE}" ] && [ -n "${SSL_OPTS_FILE}" ]; then
cat > "${SSL_OPTS_FILE}" <<EOF 
    ssl_protocols                  TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers      off;
    ssl_session_tickets            off;
    ssl_session_cache              shared:le_nginx_SSL:10m;
    ssl_session_timeout            1440m;
    ssl_ciphers "ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384"; 
EOF
fi

if [ "$1" = 'certbot' ]; then
    trap "certbot TRAPed signal" HUP INT QUIT TERM
    mkdir -p "${SSL_WEBROOT}/${DOMAIN_NAME}"
    echo "certbot verification and obtaining certificates"
    while true
    do
        "$@" --webroot -w "${SSL_WEBROOT}/${DOMAIN_NAME}" \
        --cert-name "${DOMAIN_NAME}" --email "${SSL_EMAIL}" \
        -d "${DOMAIN_NAME}" -d "www.${DOMAIN_NAME}" \
        --agree-tos --no-eff-email --noninteractive \
        --keep-until-expiring

        echo "certbot waits 12h before the next check and install of certificates."
        sleep 12h
    done
fi
