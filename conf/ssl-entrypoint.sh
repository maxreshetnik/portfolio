#!/bin/sh

trap "certbot TRAPed signal" HUP INT QUIT TERM

set -eu

openssl version

SSL_DHPARAM="${SSL_DIR}/ssl-dhparams.pem"
SSL_OPTS_FILE="${SSL_DIR}/options-ssl-nginx.conf"
SSL_WEBROOT="${SSL_DIR}/html"
CRT_DIR="${SSL_DIR}/live/${DOMAIN_NAME}"
SSL_CRT_FILE="${CRT_DIR}/fullchain.pem"
SSL_KEY_FILE="${CRT_DIR}/privkey.pem"

set +u

cat > "${SSL_OPTS_FILE}" <<EOF 
    ssl_protocols                  TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers      off;
    ssl_session_tickets            off;
    ssl_session_cache              shared:le_nginx_SSL:10m;
    ssl_session_timeout            1440m;
    ssl_ciphers "ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384"; 
EOF

if [ ! -f "${SSL_KEY_FILE}" ] || [ ! -f "${SSL_CRT_FILE}" ]; then
    mkdir -p "${CRT_DIR}"
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -outform PEM -keyform PEM -subj "/C=XX/CN=${DOMAIN_NAME}" \
    -keyout "${SSL_KEY_FILE}" -out "${SSL_CRT_FILE}" \
    || echo "Openssl fails to create key or cert: Exited $?"
fi

if [ ! -f "${SSL_DHPARAM}" ]; then
    openssl dhparam -out "${SSL_DHPARAM}" 2048 \
    || ( echo "Openssl fails to create dhparam.pem: Exited $?" ; exit 1 )
fi

if [[ "$1" = 'certbot' && "$DOMAIN_NAME" != 'localhost' ]]; then

    mkdir -p "${SSL_WEBROOT}/${DOMAIN_NAME}/.well-known/acme-challenge"
    echo "" >> "${SSL_WEBROOT}/${DOMAIN_NAME}/.well-known/acme-challenge/test.txt"
    
    echo "Check if the webroot directory is online."
    wget --spider "http://${DOMAIN_NAME}/.well-known/acme-challenge/test.txt"

    echo "Check https://${DOMAIN_NAME}"
    wget --spider "https://${DOMAIN_NAME}" || (
        echo "Try certbot verification and obtaining certificates" ;
        "$@" --webroot -w "${SSL_WEBROOT}/${DOMAIN_NAME}" \
        --cert-name "${DOMAIN_NAME}-signed" --email "${SSL_EMAIL}" \
        -d "${DOMAIN_NAME}" -d "www.${DOMAIN_NAME}" \
        --agree-tos --no-eff-email --noninteractive \
        --keep-until-expiring --expand \
        && cp -rfP ${CRT_DIR}-signed/* ${CRT_DIR}
    ) || (
        echo "Certbot can't get a certificate, use --dry-run option for testing." ;
        echo "wait for 1h before exit" ; sleep 1h ; exit 1
    )

    echo -e "
    # Enable OSCP stapling
    ssl_stapling            on;
    ssl_stapling_verify     on;
    ssl_trusted_certificate ${CRT_DIR}/chain.pem;
    " >> ${SSL_OPTS_FILE}

    echo "Run a certbot renew check every 12 hours."
    while true
    do
        certbot renew --cert-name "${DOMAIN_NAME}-signed" \
        --deploy-hook "cp -rfP ${CRT_DIR}-signed/* ${CRT_DIR}"
        sleep 12h
    done
fi
echo "Certbot won't start on localhost domain name, waiting for 12 hours before exit ..."
sleep 12h
