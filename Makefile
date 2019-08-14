DOCKER_IMAGE_URL=ddartifacts-docker.jfrog.io/doordash/$(SERVICE_NAME)
LOCAL_CHART=_infra/charts/$(SERVICE_NAME)
LOCAL_TAG=localbuild
CI_BASE_IMAGE=$(SERVICE_NAME):$(LOCAL_TAG)
CI_CONTAINER_NAME=$(SERVICE_NAME)-ci
CI_TAG=cibuild
LOCAL_RUNTIME_PATH=local-runtime
SERVICE_NAME=payment-service
SHA=$(shell git rev-parse HEAD)
ENCODED_ARTIFACTORY_USERNAME=$${ARTIFACTORY_USERNAME/@/%40}

ifeq ($(SECRETS),)
  SECRETS=env.SECRETS=none
endif

ifeq ($(CACHE_FROM),)
  CACHE_FROM=$(LOCAL_TAG)
endif

.PHONY: build
build:
	docker build -t $(SERVICE_NAME):$(LOCAL_TAG) --cache-from $(CACHE_FROM) \
	--build-arg BUILD_NUMBER="${BUILD_NUMBER}" \
	--build-arg ARTIFACTORY_USERNAME="${ARTIFACTORY_USERNAME}" \
	--build-arg ARTIFACTORY_PASSWORD="${ARTIFACTORY_PASSWORD}" \
	--build-arg FURY_TOKEN="${FURY_TOKEN}" \
	.

.PHONY: build-ci-container
build-ci-container:
	env \
	CI_IMAGE_NAME="$(SERVICE_NAME):$(CI_TAG)" \
	CI_BASE_IMAGE="$(CI_BASE_IMAGE)" \
	CI_CONTAINER_NAME="$(CI_CONTAINER_NAME)" \
	docker-compose -f docker-compose.ci.yml -f docker-compose.nodeploy.yml build \
	--build-arg CI_BASE_IMAGE="${CI_BASE_IMAGE}"

.PHONY: run-ci-container
run-ci-container: build-ci-container
	env \
	CI_IMAGE_NAME="$(SERVICE_NAME):$(CI_TAG)" \
	CI_BASE_IMAGE="$(CI_BASE_IMAGE)" \
	CI_CONTAINER_NAME="$(CI_CONTAINER_NAME)" \
	docker-compose -f docker-compose.ci.yml -f docker-compose.nodeploy.yml up -d --force-recreate --renew-anon-volumes

.PHONY: tag
tag:
	$(doorctl) tag --repourl $(DOCKER_IMAGE_URL) --localimage $(SERVICE_NAME):$(LOCAL_TAG) --sha $(SHA) --branch $(branch)

.PHONY: push
push:
	$(doorctl) push --repourl $(DOCKER_IMAGE_URL) --localimage $(SERVICE_NAME):$(LOCAL_TAG) --sha $(SHA) --branch $(branch)

.PHONY: sync-pipenv
sync-pipenv:
	env \
	ARTIFACTORY_USERNAME="$(ENCODED_ARTIFACTORY_USERNAME)" \
	ARTIFACTORY_PASSWORD="$${ARTIFACTORY_PASSWORD}" \
	pipenv sync --dev

.PHONY: update-pipenv
update-pipenv:
	env \
	ARTIFACTORY_USERNAME="$(ENCODED_ARTIFACTORY_USERNAME)" \
	ARTIFACTORY_PASSWORD="$${ARTIFACTORY_PASSWORD}" \
	pipenv update --dev

.dockerignore: .gitignore
	# skip comments (lines starting with #)
	# and directories (lines ending with /)
	# add **/ prefix to all files so they're ignored by docker
	# no matter where they are located
	sed -E '/(^#|\/$$)/! s/(.+)/**\/\1/g' .gitignore | tee .dockerignore

.PHONY: dockerignore
dockerignore: .dockerignore

.PHONY: start-local-docker-server
start-local-docker-server:
	WEB_PORT=8001 docker-compose -f docker-compose.yml -f docker-compose.nodeploy.yml up --build -d

.PHONY: stop-local-docker-server
stop-local-docker-server:
	WEB_PORT=8001 docker-compose -f docker-compose.yml -f docker-compose.nodeploy.yml down

.PHONY: local-server
local-server: local-dependency
	./development/start-local-server.sh -e local -p 8000

.PHONY: local-dependency
local-dependency:
	docker-compose -f docker-compose.nodeploy.yml up -d payment.dsj-postgres payment.stripe-mock

.PHONY: test
test: test-lint test-typing local-dependency test-unit test-external test-integration

.PHONY: test-unit
test-unit:
	python runtests.py -m "not external and not integration" app/

.PHONY: test-integration
test-integration: wait-test-dependency
	python runtests.py -m "integration" app/

.PHONY: test-pulse
test-pulse: wait-test-dependency
	ENVIRONMENT=testing python -m development.pulse_run

.PHONY: test-external
test-external:
	python runtests.py -m "external" app/

.PHONY: test-lint
test-lint:
	python -m flake8 $(FLAKE8_ADDOPTS)

.PHONY: test-typing
test-typing:
	python -m mypy -p app $(MYPY_ADDOPTS)

.PHONY: test-install-hooks
test-install-hooks:
	pre-commit install

.PHONY: test-hooks
test-hooks:
	pre-commit run --all-files $(HOOKS_ADDOPTS)

.PHONY: wait-test-dependency
wait-test-dependency:
	ENVIRONMENT=testing python -m development.waitdependencies

# Following are make targets are only needed if you want to develop based on to local k8s deployment

.PHONY: local-deploy
local-deploy:
	helm upgrade $(SERVICE_NAME) $(LOCAL_CHART) -i --force -f $(LOCAL_CHART)/values-local.yaml --set web.runtime.hostPath=$(LOCAL_RUNTIME_PATH)

.PHONY: local-status
local-status:
	helm status $(SERVICE_NAME)

.PHONY: local-bash
local-bash:
	kubectl exec -it `kubectl get pods -l service=$(SERVICE_NAME) -o jsonpath="{.items[0].metadata.name}"` --container=web bash

.PHONY: local-clean
local-clean:
	helm delete --purge $(SERVICE_NAME)

.PHONY: local-tail
local-tail:
	kubectl get pods -l service=$(SERVICE_NAME) -o jsonpath="{.items[0].metadata.name}" | xargs kubectl logs -f --container=web --tail=10
