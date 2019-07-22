#!/usr/bin/env bash

set -e

export ENVIRONMENT=local

export DSJ_DB_PORT=5435
export PAYIN_MAINDB_URL=postgresql://payin_user@localhost:${DSJ_DB_PORT}/maindb_${PROFILE:-dev}
export PAYOUT_MAINDB_URL=postgresql://payout_user@localhost:${DSJ_DB_PORT}/maindb_${PROFILE:-dev}
export PAYOUT_BANKDB_URL=postgresql://payout_user@localhost:${DSJ_DB_PORT}/bankdb_${PROFILE:-dev}

# start dependencies in docker compose
docker-compose -f docker-compose.nodeploy.yml up -d

# start local server
pipenv run uvicorn app.main:app --reload --lifespan on --host 0.0.0.0 --port ${WEB_PORT:-8000}
