ARG PYTHON_MINOR_VERSION="3.9"
ARG PYTHON_BUILD="-slim"
ARG PROJECT_NAME="portfolio"
ARG USER_DIR="/home/${PROJECT_NAME}"
ARG PROJECT_DIR="${USER_DIR}/src/${PROJECT_NAME}"

FROM python:${PYTHON_MINOR_VERSION}${PYTHON_BUILD} AS builder
ARG PYTHON_MINOR_VERSION
ARG USER_DIR
ARG PROJECT_DIR
RUN DEBIAN_FRONTEND=noninteractive apt-get update \
    && apt-get install -y --no-install-recommends \
    python${PYTHON_MINOR_VERSION}-dev libpq-dev \
    build-essential gcc \
    && rm -rf /var/lib/apt/lists/* 
WORKDIR "${USER_DIR}/.local/"
COPY requirements.txt .
RUN pip install --disable-pip-version-check --no-cache-dir \
    --prefix . gunicorn -r requirements.txt \
    && rm -rf requirements.txt
COPY . $PROJECT_DIR

FROM python:${PYTHON_MINOR_VERSION}${PYTHON_BUILD} AS prod
ARG PYTHON_MINOR_VERSION
ARG PROJECT_NAME
ARG USER_DIR
ARG PROJECT_DIR
ARG USER_UID=1000
ARG USER_GID=$USER_UID
EXPOSE 8000
RUN DEBIAN_FRONTEND=noninteractive apt-get update \
    && apt-get install -y --no-install-recommends \
    python${PYTHON_MINOR_VERSION}-dev libpq-dev curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid $USER_GID $PROJECT_NAME \
    && useradd --create-home --no-log-init \
    --gid $USER_GID --uid $USER_UID $PROJECT_NAME \
    && mkdir -p "${USER_DIR}/media" \
    && mkdir -p "${USER_DIR}/static" \
    && chown -R $USER_UID:$USER_GID $USER_DIR
USER $PROJECT_NAME
COPY --chown=$USER_UID:$USER_GID \
    --from=builder $USER_DIR $USER_DIR
WORKDIR $PROJECT_DIR
ENV PATH="${USER_DIR}/.local/bin:${PATH}" \
    PROJECT_DATA_DIR=$USER_DIR \
    DJANGO_SETTINGS_MODULE=portfolio.settings.prod
VOLUME ["${PROJECT_DATA_DIR}/media", "${PROJECT_DATA_DIR}/static"]
HEALTHCHECK --interval=1m --timeout=3s \
    CMD curl -f http://localhost:8000/ || exit 1
ENTRYPOINT ["./conf/backend-entrypoint.sh", "gunicorn", "portfolio.wsgi"]

FROM prod AS stage
USER root
RUN DEBIAN_FRONTEND=noninteractive apt-get update \
    && apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir --disable-pip-version-check \
    --prefix ${USER_DIR}/.local coverage flake8
USER $PROJECT_NAME
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PROJECT_SECRETS_FILE="${PROJECT_DIR}/conf/example-secrets.json"
ENTRYPOINT ["./conf/backend-entrypoint.sh"]
CMD ["gunicorn", "portfolio.wsgi"]
HEALTHCHECK NONE
