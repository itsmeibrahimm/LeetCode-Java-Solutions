DOCKER_IMAGE_URL=ddartifacts-docker.jfrog.io/doordash/$(SERVICE_NAME)
LOCAL_CHART=_infra/charts/$(SERVICE_NAME)
LOCAL_TAG=localbuild
LOCAL_RUNTIME_PATH=local-runtime
SERVICE_NAME=payment
SHA=$(shell git rev-parse HEAD)

ifeq ($(SECRETS),)
  SECRETS=env.SECRETS=none
endif

ifeq ($(CACHE_FROM),)
  CACHE_FROM=$(LOCAL_TAG)
endif

.PHONY: build
build:
	docker build -t $(SERVICE_NAME):$(LOCAL_TAG) --cache-from $(CACHE_FROM) \
	--build-arg ARTIFACTORY_USERNAME="${ARTIFACTORY_USERNAME}" \
	--build-arg ARTIFACTORY_PASSWORD="${ARTIFACTORY_PASSWORD}" \
	--build-arg FURY_TOKEN="${FURY_TOKEN}" \
	.

.PHONY: tag
tag:
	$(doorctl) tag --repourl $(DOCKER_IMAGE_URL) --localimage $(SERVICE_NAME):$(LOCAL_TAG) --sha $(SHA) --branch $(branch)

.PHONY: push
push:
	$(doorctl) push --repourl $(DOCKER_IMAGE_URL) --localimage $(SERVICE_NAME):$(LOCAL_TAG) --sha $(SHA) --branch $(branch)

.PHONY: local-deploy
local-deploy:
	helm upgrade $(SERVICE_NAME) $(LOCAL_CHART) -i -f $(LOCAL_CHART)/values-local.yaml --set web.runtime.hostPath=$(LOCAL_RUNTIME_PATH)

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
