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

python -m development.waitdependencies

# start local server
uvicorn app.main:app --reload --lifespan on --host 0.0.0.0 --port ${webport}
