#!/usr/bin/env bash

set -e

environment=local
webport=8000

while getopts ":e:p:" opt; do
  case ${opt} in
  e)
    environment=${OPTARG}
    ;;
  p)
    webport=${OPTARG}
    ;;
  \?)
    echo "Usage: ./start-local-server.sh [-e, testing|local|staging|prod] [-p webport number]"
    exit 1
    ;;
  esac
done

export ENVIRONMENT=${environment}
export WEB_PORT=${webport}

python -m development.waitdependencies

# start local server with gunicorn -> uvicorn -> fastapi app
gunicorn -k app.uvicorn_worker.UvicornWorker -c ./_infra/web/gunicorn_conf_local.py app.main:app
