#!/usr/bin/env bash

export ARTIFACTORY_USERNAME="${ARTIFACTORY_USERNAME/@/%40}"
export ARTIFACTORY_PASSWORD="${ARTIFACTORY_PASSWORD}"
export FURY_TOKEN="${FURY_TOKEN}"

pipenv --venv | grep 'pulse'
pulse_env_exists=$?

set -e

if [[ pulse_env_exists -ne 0 ]]
then
  echo "no pulse virtual python env found, creating a new one..."
  PIPENV_NO_INHERIT=true pipenv install --python 3.6
else
  echo "pulse python virtual env already exists: $(pipenv --venv)"
fi

echo "install / update tests dependencies ..."
pipenv run pip install -r requirements.txt

echo "install / update develoment dependencies ..."
pipenv run pip install -r dev-requirements.txt
