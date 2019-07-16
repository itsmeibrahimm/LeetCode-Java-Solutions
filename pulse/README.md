# Payment-service Pulse tests

## Background
Pulse tests are created based on project [doordash-pulse](https://github.com/doordash/doordash-pulse).

Differently from unit tests or integration tests, these test cases aim to validate target service's e2e behavior
in an actual client perspective.

## Running pulse tests locally

1. Start up your local service. This example shows with local host service (no docker):
    ```bash
    $ cd $(git rev-parse --show-toplevel) # go to payment-service top level dir
    $ make local-server # by default server runs at localhost:8081
    # you can do 'make local-server PORT=[PORT NUMBER]' to change listened port
    ```

2. Similarly to payment-service local env setup, we need to create a separate python virtual env for pulse:
    ```bash
    $ cd $(git rev-parse --show-toplevel)/pulse # come to pulse directory
    $ PIPENV_NO_INHERIT=true pipenv install -r requirements.txt# create virtual env and ignore existing virtual env in payment-service parent dir
    $ pipenv shell # activate virtual env
      # Assuming local server running at localhost:8081 , can be changed with "SERVICE_URI" in data.yml
    $ pulse --data-file=$(pipenv --venv)/infra/local/data.yaml --data-file=infra/local/data.yaml
    ```
## Update dependencies
Note: Currently doordash-pulse Jenkins build script is not fully migrated to Pipefile + pipenv.
For local development, in order to keep development process consistent with payment-service repo, we combining
old fashioned install from requirements.txt and Pipefile:
1. Add dependencies
    - Always add dependencies to `Pipefile`
2. PR and update dependencies to remote
    1. After step #1, run following command to lock `Pipefile` to `requirement.txt`
    ```bash
    pipenv lock -r > requirements.txt

    ```
    2. !!**REMEMBER**!! after locking, alwasy replace your extra index urls including your personal access tokens with this:
    ```bash
    --extra-index-url https://${ARTIFACTORY_USERNAME}:${ARTIFACTORY_PASSWORD}@ddartifacts.jfrog.io/ddartifacts/api/pypi/pypi-local/simple/

    ```
