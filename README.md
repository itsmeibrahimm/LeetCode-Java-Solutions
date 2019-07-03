
| **This README is currently under construction, please keep in mind the content could be dramtically changed before this message is removed.** |
| --- |

# Payment services mono repo
This repo contains micros services including:
- Payout service (WIP)
- Payin service (WIP)

The repo was created through python-flask-service-template [link to specific SHA used](https://github.com/doordash/python-flask-service-template/tree/6cce3e61418cdb046f0892dec50eba4635818d74)

# Table of contents

- [Architecture and Tech Stack](https://github.com/doordash/payment#architecture-and-tech-stack)
- [Development](https://github.com/doordash/payment#development)
  - [Setup Local Environment](https://github.com/doordash/payment#setup-local-environment)
  - [Run Tests](https://github.com/doordash/payment#run-tests)
  - [Local Deploy](https://github.com/doordash/payment#local-deploy)
      - [Flask](https://github.com/doordash/payment#flask)
  - [Update Dependencies](https://github.com/doordash/payment#update-dependencies)

# Architecture and Tech Stack

The `payment` is a Kubernetes pod with at least two containers:

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
- **tox** for test automation
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

# install all dependencies needed for development, including the ones installed with the --dev argument.
# --ignore-pipfile tells Pipenv to ignore the Pipfile for installation and use what’s in the Pipfile.lock
pipenv install --dev --ignore-pipfile
```

To test that everything worked, you can try:

- running unit tests, linter and mypy: `pipenv run tox`
- deploying your service on local Kubernetes: `make build local-deploy`

- Install `pre-commit` and initialize the pre-commit hooks

```bash
brew install pre-commit
pre-commit
```

## Run Tests

Use the following:

```bash
pipenv run tox # runs UTs, linter and mypy
pipenv run tox -e py37 # runs UTs only
pipenv run tox -e mypy # runs mypy only
pipenv run tox -e lint # runs linter only
```

## Local Deploy
You can deploy your service locally using the standard `Flask` command. If you want it to run in containerized mode, 
you can use either `docker-compose` or your local kubernetes cluster

### Flask
The following command will start your `Flask` app:

```bash
ENVIRONMENT=local pipenv run python -m application.main
```

## Update Dependencies

The `payment` uses `pipenv` to ensure deterministic builds.
To update a dependency, you can do the following:

```bash
pipenv install a_package [--dev] # this will update the Pipfile
pipenv lock # this wil generate your dependency graph and pin all dependencies in Pipfile.lock
```
