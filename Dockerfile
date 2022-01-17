# syntax=docker/dockerfile:1
ARG PYTHON_VERSION=3.9
ARG PYTHON_BUILD=slim
ARG PROJECT=portfolio

FROM python:${PYTHON_VERSION}-${PYTHON_BUILD} AS builder
RUN apt update && apt install --no-install-recommends -y \
    build-essential gcc python3-pip python3-dev libpq-dev \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /tmp/
RUN pip install --upgrade pip \
    && pip install --no-cache-dir --prefix /usr/local \
    gunicorn -r /tmp/requirements.txt \
    && rm -f /tmp/requirements.txt

FROM builder AS dev
ARG PROJECT
EXPOSE 8000
ENV PORTFOLIO_DATA_DIR=/usr/src/${PROJECT}
COPY ./ ${PORTFOLIO_DATA_DIR}
WORKDIR ${PORTFOLIO_DATA_DIR}
RUN chmod 555 ./conf/entrypoint.sh ./conf/init-user-db.sh \
    && groupadd -r ${PROJECT} && useradd -r -g ${PROJECT} ${PROJECT}
USER ${PROJECT}
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=portfolio.settings.dev
ENV GUNICORN_CMD_ARGS="--bind=127.0.0.1:8000 --reload"
VOLUME ["${PORTFOLIO_DATA_DIR}/static", "${PORTFOLIO_DATA_DIR}/media"]
ENTRYPOINT ["./conf/entrypoint.sh"]
CMD ["gunicorn", "portfolio.wsgi"]

FROM python:${PYTHON_VERSION}-${PYTHON_BUILD} AS prod
ARG PROJECT
EXPOSE 8000
COPY --from=builder /usr/local /usr/local
ENV PORTFOLIO_DATA_DIR=/usr/src/${PROJECT}
COPY ./ ${PORTFOLIO_DATA_DIR}
WORKDIR ${PORTFOLIO_DATA_DIR}
RUN chmod 555 ./conf/entrypoint.sh ./conf/init-user-db.sh \
    && groupadd -r ${PROJECT} && useradd -r -g ${PROJECT} ${PROJECT}
USER ${PROJECT}
ENTRYPOINT ["./conf/entrypoint.sh", "gunicorn", "portfolio.wsgi"]
