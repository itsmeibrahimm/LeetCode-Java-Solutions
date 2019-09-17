# NOTE: SERVICE OWNERS SHOULD GENERALLY NOT NEED TO MODIFY THIS FILE.
# Instead, place your tasks in the root Makefile
SHA=$(shell git rev-parse HEAD)
SERVICE_NAME=payment-service
APP=web
DOCKER_IMAGE_URL=611706558220.dkr.ecr.us-west-2.amazonaws.com/$(SERVICE_NAME)
LOCAL_TAG=$(SERVICE_NAME):localbuild

ifeq ($(CACHE_FROM),)
  CACHE_FROM=$(LOCAL_TAG)
endif

.PHONY: docker-build
docker-build:
	docker build . -t $(LOCAL_TAG) \
	--cache-from $(CACHE_FROM) \
	--build-arg BUILD_NUMBER="${BUILD_NUMBER}" \
	--build-arg RELEASE_TAG="${RELEASE_TAG}" \
	--build-arg ARTIFACTORY_USERNAME="${ARTIFACTORY_USERNAME}" \
	--build-arg ARTIFACTORY_PASSWORD="${ARTIFACTORY_PASSWORD}" \
	--build-arg FURY_TOKEN="${FURY_TOKEN}"

.PHONY: local-deploy
local-deploy:
	cd _infra/local && \
	rm -rf .terraform terraform.tfstate apply.tfplan && \
	terraform init && \
	terraform plan -out apply.tfplan && \
	terraform apply apply.tfplan

.PHONY: local-status
local-status:
	helm status $(SERVICE_NAME)-$(APP)

.PHONY: local-clean
local-clean:
	cd _infra/local && \
	terraform destroy -auto-approve

.PHONY: local-tail
local-tail:
	kubectl get pods -n $(SERVICE_NAME) -l service=$(SERVICE_NAME) -l app=$(APP) -o jsonpath="{.items[0].metadata.name}" | xargs kubectl logs -n $(SERVICE_NAME) -f --tail=10

.PHONY: tag
tag:
	docker tag $(LOCAL_TAG) $(DOCKER_IMAGE_URL):$(SHA)

.PHONY: push
push:
	docker push $(DOCKER_IMAGE_URL):$(SHA)

.PHONY: remove-docker-images
remove-docker-images:
	docker images -a --filter=reference="$(DOCKER_IMAGE_URL):$(SHA)" --format "{{.ID}}" | sort | uniq | xargs docker rmi -f

.PHONY: migrate
migrate:
	@echo "Migrated $(SERVICE_NAME) to $(tag) for $(env) within $(k8sNamespace) on $(k8sCluster)"
