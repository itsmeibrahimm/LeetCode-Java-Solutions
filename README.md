
| **This README is currently under construction, please keep in mind the content could be dramtically changed before this message is removed.** |
| --- |

# Payment services mono repo
This repo contains micros services including:
- Payout service (WIP)
- Payin service (WIP)

The repo was created through python-flask-service-template [link to specific SHA used](https://github.com/doordash/python-flask-service-template/tree/d0c2115c2c3a822bdb065dfeb45abdb87c4d1527)

# Table of contents

- [Architecture and Tech Stack](#architecture-and-tech-stack)
- [Deployment](#deployment)
- [Development](#development)
  - [Environment Setup](#environment-setup)
  - [Development Guide](#development-guide)
    - [Running server locally](#running-flask-server-locally)
    - [Running server with docker](#running-flask-server-in-docker-compose)
  - [Update Dependencies](#update-dependencies)
  - [Work with secret](#work-with-secret)
  - [(Optional) Local k8s setup](#optional-k8s-environment)
  - [Make commands reference](#make-commands-reference)


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

# Deployment
- [CD pipeline](https://deployjenkins.doordash.com/job/payment-service/job/Jenkinsfile-deploy.groovy/)
- [CI pipeline](https://generaljenkins.doordash.com/job/payment-service/job/Jenkinsfile-nodeploy.groovy/)

# Development

## Environment Setup
### Repository credentials
1. Make sure you have followed [New eng setup guide](https://github.com/doordash/doordash-eng-wiki/blob/master/docs/New-Engineer-Setup-Guide.md#25-configure-doorstep-django) to properly setup your PIP install indices by envionment variables `ARTIFACTORY_URL`,`ARTIFACTORY_USERNAME`,`ARTIFACTORY_PASSWORD` and `PIP_EXTRA_INDEX_URL`
2. After step #1, also include `FURY_TOKEN` in your `~/.bash_profile` by running:
    ```bash
    echo "export FURY_TOKEN=$(echo $PIP_EXTRA_INDEX_URL | sed -E -e 's/.*\/([^/]+)@repo.fury.io\/doordash.*/\1/')" >> ~/.bash_profile
    source ~/.bash_profile
    ```
### Python environment
1. Install python specified in `Pipefile.lock` (v3.7) through [pyenv](https://github.com/pyenv/pyenv) and [pipenv](https://github.com/pypa/pipenv) into a newly created python virtual environment.

    ```bash
    brew install pyenv pipenv
    brew upgrade pyenv pipenv
    # install all dependencies needed for development, including the ones installed with the --dev argument.
    # --ignore-pipfile tells Pipenv to ignore the Pipfile for installation and use what’s in the Pipfile.lock
    pipenv install --dev --ignore-pipfile
    ```
2. After step #1, a python virtual envionment should be created.
    1. To find where does environment locate, run `$ pipenv --venv`
    2. To start a sub-shell within create python virtual environment, run:
       ```bash
       pipenv shell
       # Try `pipenv shell --fancy` if you want to preserve your customized shell configuration from ~/.bashrc
       ```
    3. To go back to your original shell and deactivate python virtual env, simply run `$ exit`

3. To test if everything works, you can try:
    1. Activate python virtual env: `$ pipenv shell`
    2. running unit tests, linter and mypy: `$ make test`

### Pre-commit hook
1. Install `pre-commit` and initialize the pre-commit hooks; these will run before every commit

    ```bash
    brew install pre-commit
    pre-commit install
    ```
2. Run Pre-Commit Hooks

    If you want to manually run all pre-commit hooks on a repository, run `pre-commit run --all-files`. To run individual hooks use `pre-commit run <hook_id>`.

    Pre-commit `<hook_id>` are defined in `.pre-commit-config.yaml`. Example commands:
    ```bash
    pre-commit run --all-files
    pre-commit run black --all-files
    ```

## Development guide
### Running Flask server locally
```bash
make local-server
```
- Local Flask service will be running in development and debug mode.
Any code changes will lead to a service reload and therefore be reflected in real-time.
- Confirming local server is up running:
    ```bash
    curl localhost:8081/health/ # port is defined in Makefile::local-server
    ```

#### Running tests in local environment
1. Activate python virtual env: `$ pipenv shell`
2. Available test targets:
    ```bash
    make test # runs unit tests, linter, mypy (not pre-commit hooks)
    make test-unit # runs unit tests only
    make test-typing # runs mypy only
    make test-lint # runs linter only
    make test-hooks # runs pre-commit hooks only
    ```
### Running Flask server in docker-compose
```bash
make local-docker-server
```
- Similarly as `local-server`, ./app directory is binded as a volume under web docker container.
Therefore live reload is also available here.
- Confirming server is up running in docker:
    ```bash
    curl localhost:5000/health/ # docker port mapping defined in docker-compose.yml web container
    ```

### Update Dependencies
The `payment-service` uses `pipenv` to ensure deterministic builds.
To add or update a dependency, you can do the following:

1. Add or update dependency in `Pipefile` via your text editor
2. Run following command to update `Pipefile.lock` and install from updated lock file
    ```bash
    pipenv update --dev
    ```
3. After you are done, remember to open a PR to checkin the changes!

### Work with secret
Payment-service integrated with [Ninox](https://github.com/doordash/ninox/tree/master/ninox)
as source of all secret configurations, such as DB credentials and Stripe private keys.

#### Setup Ninox access locally
1. Make sure you are in google group [eng-payment@](https://groups.google.com/a/doordash.com/forum/?hl=en#!forum/eng-payment),
otherwise please ask one of payment team member to add you in.
2. Fetch `okta-prod-payment-eng-user` Okta-aws profile via:
    ```bash
    okta-aws init
    ```
    In case, you don't have `okta-aws` cli installed, follow [here](https://github.com/doordash/doordash-eng-wiki/blob/master/docs/New-Engineer-Setup-Guide.md#21-install-aws-cli)
3. Verify you have successfully fetched aws profile by:
    ```bash
    grep okta-prod-payment-eng-user ~/.aws/credentials
    # Expected output>> [okta-prod-payment-eng-user]
    ```
4. Install Ninox:
    ```bash
    brew install Ninox
    ```
   If fails, ensure you have tapped into [doordash homebrew taps](https://github.com/doordash/homebrew-tap#setup)
5. Verify Ninox user role working:
    ```bash
    cd YOUR_PAYMENT_SERVICE_REPO
    ninox -s staging_user config
    ```
    You should see output similar to following without errors:
    ```bash
    Loading team staging_user
    {'backend': 'dbd',
     'ignore_entropy_check': False,
     'kms_key_alias': 'alias/ninox/payment-service',
     'prefix': '/ninox/payment-service/',
     'profile': 'okta-prod-payment-eng-user',
     'region': 'us-west-2',
     'role': 'arn:aws:iam::016116557778:role/ninox_payment-service_xacct_user_staging',
     'session': Session(region_name='us-west-2'),
     'table': 'ninox-payment-service-staging'}
    ```
6. Ninox secret CRUD and integration
    // TODO: fill in this section after current changes checked in.

### (Optional) k8s environment

#### Setup
1. Install [docker for Mac](https://docs.docker.com/docker-for-mac/install/) and enable the local Kubernetes cluster by
  clicking on Docker whale icon > `Preferences...` > `Kubernetes` > `Enable Kubernetes`
2. Configure Kubernetes to use your local context: `kubectl config use-context docker-for-desktop`
3. Install and initialize helm:
    ```bash
    brew install kubernetes-helm

    # If your local k8s cluster complains `connection refused`, try to do the following:
    #  - remove k8s config for this local cluster in your ~/.kube/config
    #  - increase your local docker setting to have 4G swap space (Preferences -> Advanced)
    helm init
    ```
4. Try to build and deploy your service on local Kubernetes: `make build local-deploy`

#### Running service in local k8s cluster

1. Ensure that Kubernetes is configured to use your local context: `kubectl config use-context docker-for-desktop`
2. Build the docker image for your service: `make build`
3. Deploy locally: `make local-deploy`
4. Start the proxy: `kubectl proxy`
5. Query the service APIs using a REST client (e.g. `curl`):
    ```bash
    curl http://localhost:8001/api/v1/namespaces/default/services/payment-service-web:80/proxy/health
    ```


## Make commands reference

Here's a reference to all available `make` commands:

```bash
make build # use docker to build the service image

make tag # uses doorctl to tag the service image

make push # uses doorctl to push the service image to Artifactory

make build-ci-container # build the docker container for CI, using docker-compose.ci.yml

make run-ci-container # start the docker container for CI in daemon mode

make local-server # run service on your local host within python virtual env

make local-docker-server # run service with docker-compose

make test # runs unit tests, linter, mypy (not pre-commit hooks)

make test-unit # runs unit tests only

make test-typing # runs mypy only

make test-lint # runs linter only

make test-install-hooks # installs pre-commit hooks

make test-hooks # runs pre-commit hooks only
```

Also here are `make` targets if you like to deploy service to local k8s cluster
```bash
make local-deploy # uses helm to deploy the service on the local Kubernetes cluster

make local-status # uses helm to show the local service deployment status

make local-bash # opens a bash shell into the service container

make local-clean # uses helm to undeploy the local service

make local-tail # tails the local service logs

```
