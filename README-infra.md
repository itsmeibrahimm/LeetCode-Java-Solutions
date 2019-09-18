# Payment service infra
## Deployment

Payment service inherits [doordash-terraform-kubernetes-microservice](https://github.com/doordash/terraform-kubernetes-microservice) to manage terraform-helm-kubernetes deployment.

- [Terraform](https://www.terraform.io/docs/providers/helm/release.html): module/parameterize helm chart
- [Helm](https://helm.sh/): release management of kubernetes deployment
- [Kubernetes](https://kubernetes.io/): cluster running payment-service containers

### Namespace
Payment service runs separately in staging and prod kubernetes clusters with **same** namespace `payment-service`

**Note** Any `kubectl` command against local/staging/prod (via bastion) need to be appended with `-n payment-service` to specify namespace correctly now.

### Web Endpoints:
#### Ingress [prod](https://github.com/doordash/infra2/blob/master/infra/ingress/ingress/prod/payment-service.yaml) | [staging](https://github.com/doordash/infra2/blob/master/infra/ingress/ingress/staging/payment-service.yaml)

#### K8s internal endpoints
Only accessible from clients within same k8s cluster for prod and staging separately.

- prod: http://payment-service-web.payment-service.svc.cluster.local
- staging: http://payment-service-web.payment-service.svc.cluster.local

### Containers / Apps
- payment-service-web: main payment-service web service application
- payment-service-cron: cron workers
- payment-service-admin: provide operational access, such as remote python shell

### Configurations
Our helm-kubernetes deployment is parameterized by terraform modules: [local](https://github.com/doordash/payment-service/blob/master/_infra/local/service.tf) | [staging](https://github.com/doordash/payment-service/blob/master/_infra/staging/service.tf.template) | [prod](https://github.com/doordash/payment-service/blob/master/_infra/prod/service.tf.template)

Please refer to [doordash-terraform-kubernetes-microservice](https://github.com/doordash/terraform-kubernetes-microservice) for detailed available configurations in case any future infra update needs.

## Local kubernetes deployment setup (Optional)

In case need to test any kubernetes level changes locally, we can setup a local kubernetes deployment of payment-service.

**Note:** currently, we haven't fully setup local cluster deployment since other dependency containers like postgres, stripe ... are not codified into local helm chart yet.

### 1. Setup Docker

Setup Docker to use Helm to deploy local builds into a local Kubernetes cluster:

  1. Enable Kubernetes: Click on Docker whale icon > `Preferences...` > `Kubernetes` > `Enable Kubernetes`
  2. Select Context: `kubectl config use-context docker-for-desktop`<br>
     Note: If no context exists with the name `docker-for-desktop context`, then restart the cluster...<br>
     Docker whale icon > `Kubernetes` > `Disable local cluster` and then `Enable local cluster`.
  3. Install Helm: `brew install kubernetes-helm`
  4. Init Helm: `helm init`
  5. Install Terraform: `brew install terraform`


### 2. Build and Deploy

All of the following should be executed within the `service-template` directory...

To build a local Docker image: `make docker-build`

To deploy the Docker image *using* Helm to Kubernetes: `make local-deploy`

To check status *using* Helm: `make local-status`

 * Note: you are looking for the following

    ```bash
    NAME                                   READY  STATUS   RESTARTS  AGE
    payment-service-web-84754b8564-wjqfd   1/1    Running  0         1m
    ```

To tail logs *using* Kubernetes: `make local-tail`

 * Note: Press CTRL+C to quit tailing logs

To stop and clean up *using* Helm: `make local-clean`

## Troubleshooting
### Helm
You may notice your locally installed helm has different version than staing helm. When in trouble using local helm client access staging helm status, you can copy following `helm-toggle` scripts to your `~/.bash_profile` and use it to toggle between helm versions:

```bash
# See https://github.com/helm/charts/issues/5239
# brew install jq
# To install 2.11.0...
# brew unlink kubernetes-helm
# brew install https://raw.githubusercontent.com/Homebrew/homebrew-core/ee94af74778e48ae103a9fb080e26a6a2f62d32c/Formula/kubernetes-helm.rb
function helm-toggle() {
    if [ -z "$1" ]; then
        echo "helm client and Tiller (server side) versions always must match. Simply toggle between different Helm versions installed by brew".
        echo
        echo "Usage: helm-toggle <Helm version>"
        echo
        echo "installed helm versions are:"
        brew info --json=v1  kubernetes-helm | jq '.[].installed[].version'
        echo "current helm version is:"
        brew info --json=v1  kubernetes-helm | jq '.[].linked_keg'
    else
        brew switch kubernetes-helm $1 > /dev/null # no appropriate error handling here if someone sets something silly
    fi
}
```
