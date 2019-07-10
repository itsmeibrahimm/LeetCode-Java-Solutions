#!/bin/bash

# This script will start doorstep-django.postgres container and dump schemas of maindb and bankdb to:
#     payment-service/development/
#     ├── ...
#     ├── db-schemas
#     │   ├── bankdb_dump.sql ---> bankDB schema
#     │   └── maindb_dump.sql ---> mainDB schema
#     ├── ...

PROJECT_DIR=$(git rev-parse --show-toplevel)/..
ORIGINAL_DIR=$(pwd)
cd $(dirname "$0")

SCHEMA_DUMP_FOLDER=db-schemas
CONTAINER_OUTPUT_DIR=/tmp/out
SCHEMA_DUMP_DIR=${CONTAINER_OUTPUT_DIR}/${SCHEMA_DUMP_FOLDER}
MAINDB_DUMP_NAME=maindb_dump.sql
BANKDB_DUMP_NAME=bankdb_dump.sql

dsj_postgres_url=${DSJ_POSTGRES_URL:-postgresql://root@localhost:5432}
dsj_local_compose_file=${PROJECT_DIR}/doorstep-django/development/local/docker-compose.yml


if [[ ! -f ${dsj_local_compose_file} ]]; then
    echo "Expected DSJ local docker-compose file=${dsj_local_compose_file} DOES NOT exists."
    exit 1
fi

echo "Start up base postgres container"
docker-compose -f ${dsj_local_compose_file} up -d doorstep-django.postgres

echo "Waiting for DSJ postgres ready for connection"

db_ping_retries=200;
pg_isready -t 0 -d ${dsj_postgres_url}
rc=$?
while [[ rc -ne 0 && ${db_ping_retries} -gt 0 ]]; do
    pg_isready -t 0 -d ${dsj_postgres_url}
    rc=$?
    sleep 1
    db_ping_retries=$(( $db_ping_retries - 1 ))
    echo "Remaining ping retries=${db_ping_retries}"
done

if [[ ${db_ping_retries} -le 0 ]]
then
  echo "Timeout waiting for postgres, was DSJ postgres container listening to ${dsj_postgres_url}?"
  exit 1
else
  echo "DSJ postgres is ready"
fi

echo "Dumping maindb schema"
docker exec doorstep-django.postgres /bin/bash -c "mkdir -p ${SCHEMA_DUMP_DIR} \
    && pg_dump --no-acl --no-owner --schema-only \
    --dbname=doorstepdb --schema=public --exclude-table=spatial_ref_sys \
    --file=${SCHEMA_DUMP_DIR}/${MAINDB_DUMP_NAME}"

echo "Dumping bankdb schema"
docker exec doorstep-django.postgres /bin/bash -c "pg_dump --no-acl --no-owner --schema-only \
    --dbname=payments --schema=public --exclude-table=spatial_ref_sys \
    --file=${SCHEMA_DUMP_DIR}/${BANKDB_DUMP_NAME}"

docker cp doorstep-django.postgres:${SCHEMA_DUMP_DIR} ./

echo "Successfully dumped schemas at $(pwd)/${SCHEMA_DUMP_FOLDER}"

cd ${ORIGINAL_DIR}
