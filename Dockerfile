ARG PYTHON_VERSION=3.9

FROM python:${PYTHON_VERSION} AS build
ARG project=portfolio
EXPOSE 8000
ENV PORTFOLIO_DATA_DIR=/usr/src/${project}
ENV GUNICORN_CMD_ARGS="--bind=127.0.0.1:8000 --workers=3"
WORKDIR ${PORTFOLIO_DATA_DIR}
COPY requirements.txt ./
RUN pip --version $$ pip install --upgrade pip \
    $$ pip install gunicorn -r requirements.txt gunicorn
COPY . ./

FROM build AS development
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=portfolio.settings.dev
CMD ["gunicorn","--bind=127.0.0.1:8000 --reload", "portfolio.wsgi"]

FROM build AS development1
ARG user=appuser
ENV DJANGO_SETTINGS_MODULE=portfolio.settings.prod
RUN adduser -u 5678 --disabled-password --gecos "" ${user} \
    && chown -R ${user} ./
USER ${user}
CMD ["gunicorn", "portfolio.wsgi"]
