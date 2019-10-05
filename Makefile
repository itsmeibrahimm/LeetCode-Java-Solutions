include _infra/infra*.mk

CI_BASE_IMAGE=$(LOCAL_TAG)
CI_CONTAINER_NAME=$(SERVICE_NAME)-ci
CI_TAG=cibuild
ENCODED_ARTIFACTORY_USERNAME=$${ARTIFACTORY_USERNAME/@/%40}

.PHONY: build-ci-container
build-ci-container: docker-build
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
ifndef WEB_PORT
override WEB_PORT = 8000
endif
local-server: local-dependency
	./development/start-local-server.sh -e local -p $(WEB_PORT)

.PHONY: local-dependency
local-dependency:
	docker-compose -f docker-compose.nodeploy.yml up -d payment.dsj-postgres payment.stripe-mock

.PHONY: migrate
migrate:
	ENVIRONMENT=local python -m development.update_db_schemas && \
	ENVIRONMENT=testing python -m development.update_db_schemas

.PHONY: test
test: test-lint test-typing local-dependency test-unit test-external test-integration

.PHONY: test-unit
test-unit:
	python runtests.py -m "not external and not integration" app/

.PHONY: test-integration
test-integration: wait-test-dependency test-external
	python runtests.py -m "integration and not external" app/

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
	rm -rf .mypy_cache; \
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

.PHONY: local-bash
local-bash:
	kubectl exec -it `kubectl get pods -l service=$(SERVICE_NAME) -o jsonpath="{.items[0].metadata.name}"` --container=web bash
