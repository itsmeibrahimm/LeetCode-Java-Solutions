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

# this directory needs to exist for gunicorn worker heartbeats
# in production, a tmpfs will be mounted here
RUN mkdir -p /tmpfs

WORKDIR /home

COPY \
  Makefile \
  .flake8 \
  pytest.ini \
  mypy.ini \
  runtests.py \
  Pipfile \
  Pipfile.lock \
  ninox.ini \
  ./

RUN apt-get update -y && \
  apt-get install -y -qq --no-install-recommends \
  build-essential \
  python-dev \
  procps \
  vim \
  curl && \
  python -m pip install --upgrade pip setuptools pipenv

RUN env ARTIFACTORY_USERNAME=$(echo ${ARTIFACTORY_USERNAME} | sed "s|@|%40|g") \
  pipenv install --ignore-pipfile --deploy --system

RUN apt-get clean && \
  rm -rf /root/.cache

COPY _infra/web/gunicorn_conf.py /home/
COPY app /home/app
COPY development /home/development

# Use a tmpfs mount to prevent heartbeat blocking event loop for EBS volumes
# http://docs.gunicorn.org/en/stable/faq.html#how-do-i-avoid-gunicorn-excessively-blocking-in-os-fchmod
CMD ["gunicorn", "--worker-tmp-dir", "/tmpfs", "-k", "uvicorn.workers.UvicornWorker", "-c", "./gunicorn_conf.py", "app.main:app"]
