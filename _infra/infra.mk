# NOTE: SERVICE OWNERS SHOULD GENERALLY NOT NEED TO MODIFY THIS FILE.
# Instead, place your tasks in the root Makefile
SHA=$(shell git rev-parse HEAD)
SERVICE_NAME=payment-service
APP=web
NAMESPACE=$(SERVICE_NAME)
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
	bash ../common-pipelines/src/scripts/deploy-service.sh -c local -n $(NAMESPACE) -s $(SERVICE_NAME) -t localbuild

.PHONY: local-status
local-status:
	helm status $(SERVICE_NAME)-$(APP)

.PHONY: local-rollout-status
local-rollout-status:
	kubectl -n $(NAMESPACE) rollout status deployment $(SERVICE_NAME)-$(APP)

.PHONY: local-rollout-undo
local-rollout-undo:
	kubectl -n $(NAMESPACE) rollout undo deployment $(SERVICE_NAME)-$(APP)

.PHONY: local-clean
local-clean:
	cd _infra/local && terraform destroy -auto-approve || true
	helm --kube-context docker-for-desktop delete --purge $(SERVICE_NAME)-$(APP) || true
	rm -rf _infra/local/.terraform _infra/local/terraform.tfstate* _infra/local/apply.tfplan

.PHONY: local-get-all
local-get-all:
	kubectl -n $(NAMESPACE) get ingress,service,deployment,rollout,configmap,secret,horizontalpodautoscaler,replicaset,pod

.PHONY: local-get-all-running
local-get-all-running:
	while true; do echo "" ; echo "----------------" ; date ; echo "----------------" ; echo "" ; kubectl -n $(NAMESPACE) get ingress,service,deployment,rollout,configmap,secret,horizontalpodautoscaler,replicaset,pod ; sleep 1 ; done

.PHONY: local-describe-all
local-describe-all:
	kubectl -n $(NAMESPACE) describe ingress,service,deployment,rollout,configmap,secret,horizontalpodautoscaler,pod

.PHONY: local-get-events
local-get-events:
	kubectl -n $(NAMESPACE) get events --sort-by='.metadata.creationTimestamp'

.PHONY: local-describe
local-describe:
	kubectl describe -n $(NAMESPACE) pod `kubectl get pods -n $(NAMESPACE) -l service=$(SERVICE_NAME) -l app=$(APP) -o jsonpath="{.items[0].metadata.name}"`

.PHONY: local-config
local-config:
	kubectl get configmaps --namespace kube-system $(SERVICE_NAME)-$(APP).v`kubectl get configmaps --namespace kube-system | grep $(SERVICE_NAME)-$(APP) | cut -d" " -f1 | cut -d"." -f2 | cut -d"v" -f2 | sort -n | tail -1` -o jsonpath='{.data.release}' | base64 -D | gunzip

.PHONY: local-tail
local-tail:
	kubectl logs -n $(NAMESPACE) -f --tail=10 `kubectl get pods -n $(NAMESPACE) -l service=$(SERVICE_NAME) -l app=$(APP) -o jsonpath="{.items[0].metadata.name}"` $(APP)

.PHONY: local-bash
local-bash:
	kubectl exec -n $(NAMESPACE) -it `kubectl get pods -n $(NAMESPACE) -l service=$(SERVICE_NAME) -l app=$(APP) -o jsonpath="{.items[0].metadata.name}"` --container=$(APP) bash

.PHONY: local-bash-to-pod
local-bash-to-pod: guard-POD
	kubectl exec -n $(NAMESPACE) -it ${POD} --container=$(APP) bash

.PHONY: local-port-forward
local-port-forward:
	kubectl -n $(NAMESPACE) port-forward svc/$(SERVICE_NAME)-$(APP) 7001:80

.PHONY: local-times
local-times:
	kubectl -n $(NAMESPACE) get pods -o json | egrep '[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z' | cut -d'"' -f4 | sort | awk 'NR==1; END{print}'

.PHONY: local-running-count
local-running-count:
	while true ; do echo "---" ; date ; kubectl -n $(NAMESPACE) get pods -o json | jq -c '.items[] | (if .metadata.deletionTimestamp == null then (.status.phase + " " + ([select(.status.containerStatuses[].ready == true)] | length | tostring) + "/" + (.status.containerStatuses | length | tostring)) else "Terminating" end) + " " + .spec.containers[].image + " " + .metadata.labels["pod-template-hash"] + .metadata.labels["rollouts-pod-template-hash"]' | grep -v runtime | sort | uniq -c ; sleep 2 ; done

.PHONY: tag
tag:
	docker tag $(LOCAL_TAG) $(DOCKER_IMAGE_URL):$(SHA)

.PHONY: push
push:
	docker push $(DOCKER_IMAGE_URL):$(SHA)

.PHONY: remove-docker-images
remove-docker-images:
	docker images -a --filter=reference="$(DOCKER_IMAGE_URL):$(SHA)" --format "{{.ID}}" | sort | uniq | xargs -r docker rmi -f

.PHONY: migrate
migrate:
	@echo "Migrated $(SERVICE_NAME) to $(tag) for $(env) within $(k8sNamespace) on $(k8sCluster)"

.PHONY: local-argo-rollouts-get
local-argo-rollouts-get:
	kubectl argo rollouts get rollout $(SERVICE_NAME)-$(APP) -n $(NAMESPACE) --no-color

.PHONY: local-argo-rollouts-watch
local-argo-rollouts-watch:
	kubectl argo rollouts get rollout $(SERVICE_NAME)-$(APP) -n $(NAMESPACE) --no-color --watch

.PHONY: local-argo-rollouts-manual-promote
local-argo-rollouts-manual-promote:
	kubectl argo rollouts promote $(SERVICE_NAME)-$(APP) -n $(NAMESPACE)

.PHONY: local-argo-rollouts-patch-replicas
local-argo-rollouts-patch-replicas: guard-REPLICAS
	kubectl -n $(NAMESPACE) patch rollout $(SERVICE_NAME)-$(APP) --type=merge -p '{"spec":{"replicas":$(REPLICAS)}}'

.PHONY: local-argo-rollouts-bounce
local-argo-rollouts-bounce:
	kubectl -n $(NAMESPACE) patch rollout $(SERVICE_NAME)-$(APP) --type=merge -p '{"spec":{"template":{"metadata":{"annotations":{"bounce-date":"'`date +%s`'"}}}}}'

.PHONY: local-rolling-update-bounce
local-rolling-update-bounce:
	kubectl -n $(NAMESPACE) patch deployment $(SERVICE_NAME)-$(APP) --type=merge -p '{"spec":{"template":{"metadata":{"annotations":{"bounce-date":"'`date +%s`'"}}}}}'

# task "guard-[X]" checks to see if the $[X] environment variable is set
guard-%:
	@ if [ "${${*}}" = "" ]; then \
		echo "variable $* not set"; \
		exit 1; \
	fi
