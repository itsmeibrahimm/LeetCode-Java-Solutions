#!/usr/bin/env bash

set -e

environment=local

while getopts ":e:t:p:c:" opt; do
  case ${opt} in
  e)
    environment=${OPTARG}
    ;;
  t)
    topic_name=${OPTARG}
    ;;
  p)
    processor=${OPTARG}
    ;;
  c)
    num_consumers=${OPTARG}
    ;;
  \?)
    echo "Usage: ./start-local-worker.sh [-e, testing|local|staging|prod] [-p processor] [-t topic_name] [-c num_consumers]"
    exit 1
    ;;
  esac
done

export ENVIRONMENT=${environment}

python -m development.waitdependencies

# start local worker
python -m app.worker --topic_name ${topic_name} --processor ${processor} --num_consumers ${num_consumers}
