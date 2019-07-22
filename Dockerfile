FROM python:3.7-slim

ARG ARTIFACTORY_USERNAME
RUN : "${ARTIFACTORY_USERNAME:?Requires ARTIFACTORY_USERNAME}"

ARG ARTIFACTORY_PASSWORD
RUN : "${ARTIFACTORY_PASSWORD:?Requires ARTIFACTORY_PASSWORD}"

ARG FURY_TOKEN
RUN : "${FURY_TOKEN:?Requires FURY_TOKEN}"

ENV ARTIFACTORY_USERNAME ${ARTIFACTORY_USERNAME}
ENV ARTIFACTORY_PASSWORD ${ARTIFACTORY_PASSWORD}
ENV FURY_TOKEN ${FURY_TOKEN}

ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8
ENV PY_IGNORE_IMPORTMISMATCH=1

WORKDIR /home

COPY \
  Makefile \
  .flake8 \
  mypy.ini \
  runtests.py \
  Pipfile \
  Pipfile.lock ./

RUN apt-get update -y && \
  apt-get install -y -qq --no-install-recommends \
  build-essential \
  python-dev \
  procps \
  vim \
  curl && \
  python -m pip install --upgrade pip setuptools pipenv && \
  pipenv install --ignore-pipfile --deploy --system && \
  apt-get clean && \
  rm -rf /root/.cache

COPY _infra/web/gunicorn_conf.py /home/
COPY app /home/app

CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-c", "./gunicorn_conf.py", "app.main:app"]
