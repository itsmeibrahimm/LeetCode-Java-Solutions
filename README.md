
| **This README is currently under construction, please keep in mind the content could be dramtically changed before this message is removed.** |
| --- |

# Payment services mono repo
This repo contains micros services including:
- Payout service (WIP)
- Payin service (WIP)

The repo was created through python-flask-service-template [link to specific SHA used](https://github.com/doordash/python-flask-service-template/tree/d0c2115c2c3a822bdb065dfeb45abdb87c4d1527)

# Table of contents

- [Architecture and Tech Stack](https://github.com/doordash/payment-service#architecture-and-tech-stack)
- [Development](https://github.com/doordash/payment-service#development)
  - [Setup Local Environment](https://github.com/doordash/payment-service#setup-local-environment)
  - [Run Tests](https://github.com/doordash/payment-service#run-tests)
  - [Local Deploy](https://github.com/doordash/payment-service#local-deploy)
    - [Flask](https://github.com/doordash/payment-service#flask)
    - [docker-compose](https://github.com/doordash/payment-service#docker-compose)
    - [Kubernetes](https://github.com/doordash/payment-service#kubernetes)
  - [Update Dependencies](https://github.com/doordash/payment-service#update-dependencies)
  - [Make commands reference](https://github.com/doordash/payment-service#make-commands-reference)

# Architecture and Tech Stack

The `payment-service` is a Kubernetes pod with at least two containers:

- the `web` container, which runs a `flask` app behind a `uwsgi` web server
- the `nginx` sidecar, which shares a `socket` with the `web` container to perform reverse proxying and queuing
- (optional) the `runtime` sidecar, used for configuration management

The following technologies/frameworks are used across the entire stack:

- **helm** for deployments and rollbacks
- **docker** as container engine
- **kubernetes** as container orchestrator
- **python3.7** for application code
- **nginx** as reverse proxy
- **uwsgi** as WSGI web server
- **flask** as web framework
- **pipenv** for dependency management and [deterministic builds](https://realpython.com/pipenv-guide/)
- **pytest** for unit testing
- **mypy** for static type checking
- **flake8** for linting
- **black** for code formatting
- **pre-commit** for pre-commit hooks
- **DoorDash doorctl** for images tagging/pushing
- **DoorDash Pulse** for semantic monitoring
- **DoorDash Pressure** for load testing
- **DoorDash Runtime** for configuration management
- **Artifactory** to store docker images
- **Jenkins/Groovy** for CICD

# Development

## Setup Local Environment

To setup your local dev environment, please clone your repo, `cd` into it and follow these steps:

- Install [docker for Mac](https://docs.docker.com/docker-for-mac/install/) and enable the local Kubernetes cluster by
  clicking on Docker whale icon > `Preferences...` > `Kubernetes` > `Enable Kubernetes`
- Configure Kubernetes to use your local context: `kubectl config use-context docker-for-desktop`
- Install and initialize helm:

```bash
brew install kubernetes-helm
helm init
```

- Export the `FURY_TOKEN` environment variable (you may want to add the export to your `bash_profile`):

```bash
export FURY_TOKEN="YOUR_GEMFURY_TOKEN_HERE"
```

- Run the following commands:

```bash
brew install pyenv pipenv
brew upgrade pyenv pipenv
pipenv install

# install all dependencies needed for development, including the ones installed with the --dev argument.
# --ignore-pipfile tells Pipenv to ignore the Pipfile for installation and use what’s in the Pipfile.lock
pipenv install --dev --ignore-pipfile
```

To test that everything worked, you can try:

- running unit tests, linter and mypy: `make test`
- deploying your service on local Kubernetes: `make build local-deploy`

- Install `pre-commit` and initialize the pre-commit hooks; these will run before every commit

```bash
brew install pre-commit
pre-commit install
```

## Run Tests

Use the following:

```bash
make test # runs unit tests, linter, mypy (not pre-commit hooks)
make test-unit # runs unit tests only
make test-typing # runs mypy only
make test-lint # runs linter only

make test-hooks # runs pre-commit hooks only
```

### Run Pre-Commit Hooks

Pre-commit hooks run automatically when you commit code.

If you want to manually run all pre-commit hooks on a repository, run `pre-commit run --all-files`. To run individual hooks use `pre-commit run <hook_id>`.

```bash
pre-commit run --all-files
pre-commit run black --all-files
```

## Local Deploy

You can deploy your service locally using the standard `Flask` command. If you want it to run in containerized mode,
you can use either `docker-compose` or your local kubernetes cluster

### Flask

The following command will start your `Flask` app:

```bash
ENVIRONMENT=local pipenv run python -m application.main
```

### docker-compose

If you want to deploy your service locally using `docker-compose`, just type:

```bash
docker-compose up [-d] [--build]
```

You can verify that your service is up using any REST client to hit any endpoint e.g. `http://localhost:5000/health/`

### Kubernetes

If you want to deploy your service on the local Kubernetes cluster:

1. Ensure that Kubernetes is configured to use your local context: `kubectl config use-context docker-for-desktop`
2. Build the docker image for your service: `make build`
3. Deploy locally: `make local-deploy`
4. Start the proxy: `kubectl proxy`
5. Query the service APIs using a REST client (e.g. `curl`):

```bash
curl http://localhost:8001/api/v1/namespaces/default/services/payment-service-web:80/proxy/health
```

You can also [run your Pulse tests locally](https://github.com/doordash/doordash-pulse#local-pulse-testing) against your service endpoints.

## Update Dependencies

The `payment-service` uses `pipenv` to ensure deterministic builds.
To update a dependency, you can do the following:

```bash
pipenv install a_package [--dev] # this will update the Pipfile
pipenv lock # this wil generate your dependency graph and pin all dependencies in Pipfile.lock
```

## Make commands reference

Here's a reference to all available `make` commands:

```bash
make build # use docker to build the service image

make tag # uses doorctl to tag the service image

make push # uses doorctl to push the service image to Artifactory

make build-ci-container # build the docker container for CI, using docker-compose.ci.yml

make run-ci-container # start the docker container for CI in daemon mode

make local-deploy # uses helm to deploy the service on the local Kubernetes cluster

make local-status # uses helm to show the local service deployment status

make local-bash # opens a bash shell into the service container

make local-clean # uses helm to undeploy the local service

make local-tail # tails the local service logs

make test # runs unit tests, linter, mypy (not pre-commit hooks)

make test-unit # runs unit tests only

make test-typing # runs mypy only

make test-lint # runs linter only

make test-install-hooks # installs pre-commit hooks

make test-hooks # runs pre-commit hooks only
```
