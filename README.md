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
      - [docker-compose](https://github.com/doordash/payment#docker-compose)
      - [Kubernetes](https://github.com/doordash/payment#kubernetes)
  - [Update Dependencies](https://github.com/doordash/payment#update-dependencies)
  - [Make commands reference](https://github.com/doordash/payment#make-commands-reference)
  - [Github repo settings](https://github.com/doordash/payment#github-repo-settings)
    - [Jenkins related settings](https://github.com/doordash/payment#jenkins-related-settings)
    - [Required CI checks](https://github.com/doordash/payment#required-ci-checks)
- [Deployment](https://github.com/doordash/payment#deployment)
  - [Pipeline](https://github.com/doordash/payment#pipeline)
  - [Ingress](https://github.com/doordash/payment#ingress)
  - [Rollback](https://github.com/doordash/payment#rollback)
- [Advanced](https://github.com/doordash/payment#advanced)
  - [Modify nginx sidecar settings](https://github.com/doordash/payment#modify-nginx-sidecar-settings)
  - [Modify uwsgi settings](https://github.com/doordash/payment#modify-uwsgi-settings)
- [Questions/Comments](https://github.com/doordash/payment#questions-comments)
  - [Frequently Asked Questions](https://github.com/doordash/payment#frequently-asked-questions)

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
curl http://localhost:8001/api/v1/namespaces/default/services/payment-web:80/proxy/health
```

You can also [run your Pulse tests locally](https://github.com/doordash/doordash-pulse#local-pulse-testing) against your service endpoints.

## Update Dependencies

The `payment` uses `pipenv` to ensure deterministic builds.
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

make local-deploy # uses helm to deploy the service on the local Kubernetes cluster

make local-status # uses helm to show the local service deployment status

make local-bash # opens a bash shell into the service container

make local-clean # uses helm to undeploy the local service

make local-tail # tails the local service logs
```

## Github repo settings

### Jenkins related settings

In order for `[general|deploy]jenkins` to be able to pick up your `Jenkinsfile-[no]*deploy.groovy` and create your service
CI and CD jobs, you'll need to add `Engineering` as collaborator with `Write` access in your repo's Settings. After
[your first PR is created](https://github.com/doordash/payment#from-zero-to-prod) you should see the
CI checks being performed. You should probably consider [setting these CI checks as required](https://github.com/doordash/payment#required-ci-checks).

### Required CI checks

Once Jenkins runs your CI checks you should set them as required and also prevent people from merging PRs that don't
have at least an approval from a reviewer. Both things can be done by adding a Branch Protection rule for `master`
under your repo's Settings -> Branches.

# Deployment

## Pipeline

The `payment` comes with a CICD pipeline out of the box, in the form of the usual `Jenkinsfile-[no]*deploy.groovy`.
Please make sure you configure all [Jenkins related settings](https://github.com/doordash/payment#jenkins-related-settings)
for the CICD to work.

The **CI** will by default run the following checks:

- `Startup`: settings and shared code loading
- `Docker Build Tag Push`: build tag and push the service docker image, possibly leveraging cache
- `Run CI container`: start the service in a container so that all subsequent checks can re-use the tox environment
- `Unit Tests`: run Unit Tests using the service ci container
- `Linting`: run flake8 using the service ci container
- `Typing`: run mypy using the service ci container

The **CD** will go through these stages:

- `Docker Build Tag Push`: build tag and push the service docker image, possibly leveraging cache
- `Unit Tests`: start a service ci container and run Unit Tests using it
- `Deploy to staging`: deploy the service to staging
- `Deploy Pulse to staging`: deploy Pulse to staging
- `Continue to prod?`: asks the user to confirm if the pipeline should proceed with prod deployment
- `Deploy to prod`: deploy the service to prod
- `Deploy Pulse to prod`: deploy Pulse to prod

## Ingress

If you want a DNS entry for your service, please refer to [this PR](https://github.com/doordash/infra2/pull/439/files)
for the files you will need to create and their location. Then [#ask-pe](https://doordash.slack.com/app_redirect?channel=ask-pe) to apply it.

## Rollback

As of now you can rollback your helmified service using [this](https://deployjenkins.doordash.com/job/microservice/job/microservice-rollback/) Jenkins job.

# Advanced

## Modify nginx sidecar settings

Nginx uses two config files: `nginx.conf` for nginx specific configurations and `flask-app.conf`
for settings related to `nginx/flask` communication. Both are uploaded to the nginx sidecar in
the form on `configmaps`, located at `_infra/charts/payment/templates/configmap.yaml`.
Please refer to [nginx official docs](https://www.nginx.com/resources/wiki/start/) for nginx configuration settings.

## Modify uwsgi settings

Uwsgi config file, `uwsgi.ini`, is located at `_infra/charts/web/uwsgi.ini`
Please refer to [uwsgi official docs](https://uwsgi-docs.readthedocs.io/en/latest/index.html) for uwsgi configuration settings.

# Questions? Comments?

Please check our [FAQs](https://github.com/doordash/payment#frequently-asked-questions) first.
If you don't find the answer to your question, ping us on [#ask-devprod](https://doordash.slack.com/app_redirect?channel=ask-devprod)

## Frequently Asked Questions

**Q**: I don't see my CI checks in my first PR, what should I do?

**A**: Please ensure your repo has the required [Jenkins related settings](https://github.com/doordash/payment#jenkins-related-settings)
and that the CI checks are marked as [required](https://github.com/doordash/payment#required-ci-checks).
