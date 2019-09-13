#!/usr/bin/env bash

export ARTIFACTORY_USERNAME="${ARTIFACTORY_USERNAME/@/%40}"
export ARTIFACTORY_PASSWORD="${ARTIFACTORY_PASSWORD}"
export FURY_TOKEN="${FURY_TOKEN}"

pipenv --venv | grep 'pressure'
pressure_env_exists=$?

set -e

if [[ pressure_env_exists -ne 0 ]]
then
  echo "no pressure virtual python env found, creating a new one..."
  PIPENV_NO_INHERIT=true pipenv install --python 3.6
else
  echo "pressure python virtual env already exists: $(pipenv --venv)"
fi

echo "install / update tests dependencies ..."
pipenv run pip install -r requirements.txt

echo "install / update develoment dependencies ..."
pipenv run pip install -r dev-requirements.txt
