import org.doordash.Docker
import org.doordash.Doorctl
import org.doordash.Github
import org.doordash.Pulse
import java.util.Arrays
import org.jenkinsci.plugins.workflow.steps.FlowInterruptedException

gitUrl = params["GITHUB_REPOSITORY"]
sha = params["SHA"]

/**
 * Returns the service name which is useful for builds and deployments.
 */
def getServiceName() {
  return "payment-service"
}

/**
 * Returns the service slack channel which is useful for notifying of builds and deployments.
 */
def getSlackChannel() {
  return "eng-payment-cd"
}

/**
 * Installs terraform into the _infra directory when it doesn't exist.
 */
def installTerraform() {
  sh """|#!/bin/bash
        |set -ex
        |
        |# Install Terraform
        |pushd _infra
        |rm -rf terraform
        |wget -q -nc https://releases.hashicorp.com/terraform/0.12.7/terraform_0.12.7_linux_amd64.zip
        |unzip terraform_0.12.7_linux_amd64.zip
        |chmod +x terraform
        |popd
        |""".stripMargin()
}

/**
 * Build, Tag, and Push a Docker image for a Microservice.
 * If there already exists a docker image for the sha, then it will skip 'make docker-build tag push'.
 * <br>
 * <br>
 * Requires:
 * <ul>
 * <li>Makefile with docker-build, tag, push, and remove-docker-images targets
 * </ul>
 * Provides the docker-build target in Makefile with:
 * <ul>
 * <li>CACHE_FROM = url:tag of recent Docker image to speed up subsequent builds that use the --cache-from option
 * <li>env.ARTIFACTORY_USERNAME = Artifactory Username to install Python packages
 * <li>env.ARTIFACTORY_PASSWORD = Artifactory Password to install Python packages
 * <li>env.FURY_TOKEN = Gemfury Token to install Python packages
 * </ul>
 */
def dockerBuild(Map optArgs = [:], String gitUrl, String sha) {
  String gitRepo = getGitRepoName(gitUrl)
  Map o = [
    dockerImageUrl: "611706558220.dkr.ecr.us-west-2.amazonaws.com/${gitRepo}",
  ] << optArgs

  // Ensure we have a SHA
  if (sha == null) {
    error("Git SHA is required.")
  }

  // Try to pull an already pushed docker image from ECR
  String loadedCacheDockerTag
  try {
    sh """|#!/bin/bash
          |set -ex
          |docker pull ${o.dockerImageUrl}:${sha}
          |""".stripMargin()
    println "Docker image was found for ${o.dockerImageUrl}:${sha} - Skipping 'make docker-build tag push'"
    loadedCacheDockerTag = sha
  } catch (oops) {
    println "No docker image was found for ${o.dockerImageUrl}:${sha} - Running 'make docker-build tag push'"
  }

  // Build, tag, and push docker image when it isn't in ECR
  String tag = null
  try {
    tag = getImmutableReleaseSemverTag(sha)
  } catch (err) {
    println "Sha does not have an associated semver tag."
  }
  if (loadedCacheDockerTag == null || tag != null) {
    loadedCacheDockerTag = new Docker().findAvailableCacheFrom(gitUrl, sha, o.dockerImageUrl)
    if (loadedCacheDockerTag == null) {
      loadedCacheDockerTag = "noCacheFoundxxxxxxx"
    }
    String cacheFromValue = "${o.dockerImageUrl}:${loadedCacheDockerTag}"

    // Use Terraform to create the ECR Repo when it doesn't exist
    installTerraform()
    sshagent (credentials: ['DDGHMACHINEUSER_PRIVATE_KEY']) { // Required for terraform to git clone
      sh """|#!/bin/bash
            |set -ex
            |pushd _infra/build
            |rm -rf .terraform terraform.*
            |sed 's/_GITREPO_/${gitRepo}/g' ecr.tf.template > ecr.tf
            |terraform="${WORKSPACE}/_infra/terraform"
            |\${terraform} init
            |\${terraform} plan -out terraform.tfplan -var="service_name=${getServiceName()}"
            |\${terraform} apply terraform.tfplan
            |popd
            |""".stripMargin()
    }

    // Build, tag, and push the sha to ECR
    tag = tag ?: 'unknown'
    withCredentials([
      string(credentialsId: 'ARTIFACTORY_MACHINE_USER_NAME', variable: 'ARTIFACTORY_USERNAME'),
      string(credentialsId: 'ARTIFACTORY_MACHINE_USER_PASS_URLENCODED', variable: 'ARTIFACTORY_PASSWORD'),
      string(credentialsId: 'FURY_TOKEN', variable: 'FURY_TOKEN')
    ]) {
      sh """|#!/bin/bash
            |set -ex
            |make docker-build tag push \\
            | CACHE_FROM=${cacheFromValue} \\
            | RELEASE_TAG=${tag}
            |""".stripMargin()
    }
  }

  // If semver is associated with sha, tag and push the semver to ECR
  if (tag != null) {
    sh """|#!/bin/bash
          |set -ex
          |docker tag ${o.dockerImageUrl}:${sha} ${o.dockerImageUrl}:${tag}
          |docker push ${o.dockerImageUrl}:${tag}
          |# Add latest tag for security scans of our latest docker images
          |docker tag ${o.dockerImageUrl}:${sha} ${o.dockerImageUrl}:latest
          |docker push ${o.dockerImageUrl}:latest
          |""".stripMargin()
  }
}

/**
 * Runs a local container useful to run CI tests on
 */
def runCIcontainer(Map optArgs = [:], String gitUrl, String sha) {
  String gitRepo = getGitRepoName(gitUrl)
  Map o = [
    dockerImageUrl: "611706558220.dkr.ecr.us-west-2.amazonaws.com/${gitRepo}",
  ] << optArgs
  String serviceName = getServiceName()
  def imageTag = sha
  try {
    imageTag = getImmutableReleaseSemverTag(sha)
  } catch (err) {
    println "Sha does not have an associated semver tag. Using SHA as tag."
  }
  new Github().doClosureWithStatus({
    withCredentials([
      string(credentialsId: 'ARTIFACTORY_MACHINE_USER_NAME', variable: 'ARTIFACTORY_USERNAME'),
      string(credentialsId: 'ARTIFACTORY_MACHINE_USER_PASS_URLENCODED', variable: 'ARTIFACTORY_PASSWORD'),
      string(credentialsId: 'FURY_TOKEN', variable: 'FURY_TOKEN')
    ]) {
      sh """|#!/bin/bash
          |set -eox
          |docker rm ${serviceName}-ci || true
          |make run-ci-container \\
          |    CI_BASE_IMAGE="${o.dockerImageUrl}:${imageTag}" \\
          |    CI_CONTAINER_NAME="${serviceName}-ci"
          |""".stripMargin()
    }
  }, gitUrl, sha, "Unit Tests", "${BUILD_URL}testReport")
}


def loadJunit(fileName) {
  def fe = fileExists "${fileName}"
  if(fe) {
    junit "${fileName}"
    archiveArtifacts artifacts: "${fileName}"
  } else {
    currentBuild.result = 'UNSTABLE'
  }
}


/**
 * Run Unit Tests on the CI container and archive the report
 */
def runUnitTests() {
  String serviceName = getServiceName()
  def outputFile = "pytest-unit.xml"
  new Github().doClosureWithStatus({
    try {
      sh """|#!/bin/bash
            |set -eox
            |docker exec ${serviceName}-ci make test-unit PYTEST_ADDOPTS="--junitxml ${outputFile} --vcr-record=none"
            |""".stripMargin()
    } finally {
      sh """|#!/bin/bash
            |set -eox
            |docker cp ${serviceName}-ci:/home/${outputFile} ${outputFile}
            |""".stripMargin()
      loadJunit(outputFile)
    }
  }, gitUrl, sha, "Unit Tests", "${BUILD_URL}testReport")
}



/**
 * Run Integration Tests on the CI container and archive the report
 */
def runIntegrationTests() {
  String serviceName = getServiceName()
  def outputFile = "pytest-integration.xml"
  new Github().doClosureWithStatus({
    try {
      sh """|#!/bin/bash
            |set -eox
            |docker exec ${serviceName}-ci make test-integration PYTEST_ADDOPTS="--junitxml ${outputFile} \
             --vcr-record=none"
            |""".stripMargin()
    } finally {
      sh """|#!/bin/bash
            |set -eox
            |docker cp ${serviceName}-ci:/home/${outputFile} ${outputFile}
            |""".stripMargin()
      loadJunit(outputFile)
    }
  }, gitUrl, sha, "Integration Tests", "${BUILD_URL}testReport")
}


/**
 * Run Pulse Tests on the CI container and archive the report
 */
def runPulseTests() {
  String serviceName = getServiceName()
  def outputFile = "pulse-test.xml"
  new Github().doClosureWithStatus({
    withCredentials([
        string(credentialsId: 'ARTIFACTORY_MACHINE_USER_NAME', variable: 'ARTIFACTORY_USERNAME'),
        string(credentialsId: 'ARTIFACTORY_MACHINE_USER_PASS_URLENCODED', variable: 'ARTIFACTORY_PASSWORD'),
        string(credentialsId: 'FURY_TOKEN', variable: 'FURY_TOKEN')
      ]){
    try {
      sh """|#!/bin/bash
            |set -eox
            |docker exec ${serviceName}-ci make test-pulse PYTEST_ADDOPTS="--junitxml ${outputFile}"
            |""".stripMargin()
    } finally {
      sh """|#!/bin/bash
            |set -eox
            |docker cp ${serviceName}-ci:/home/pulse/${outputFile} ${outputFile}
            |""".stripMargin()
      loadJunit(outputFile)
    }}
  }, gitUrl, sha, "Pulse Tests", "${BUILD_URL}testReport")
}


/**
 * Run the linter on the CI container and archive the report
 */
def runLinter() {
  String serviceName = getServiceName()
  def outputFile = "flake8.xml"
  new Github().doClosureWithStatus({
    try {
      sh """|#!/bin/bash
            |set -eox
            |docker exec ${serviceName}-ci make test-lint FLAKE8_ADDOPTS="--format junit-xml --output-file=${outputFile}"
            |""".stripMargin()
    } finally {
      sh """|#!/bin/bash
            |set -eox
            |docker cp ${serviceName}-ci:/home/${outputFile} ${outputFile}
            |""".stripMargin()
      loadJunit(outputFile)
    }
  }, gitUrl, sha, "Linting", "${BUILD_URL}testReport")
}


/**
 * Run the static type checker on the CI container and archive the report
 */
def runTyping() {
  String serviceName = getServiceName()
  def outputFile = "mypy.xml"
  new Github().doClosureWithStatus({
    try {
      sh """|#!/bin/bash
            |set -eox
            |docker exec ${serviceName}-ci make test-typing MYPY_ADDOPTS="--junit-xml ${outputFile}"
            |""".stripMargin()
    } finally {
      sh """|#!/bin/bash
            |set -eox
            |docker cp ${serviceName}-ci:/home/${outputFile} ${outputFile}
            |""".stripMargin()
      loadJunit(outputFile)
    }
  }, gitUrl, sha, "Typing", "${BUILD_URL}testReport")
}

def commentHooksFailed() {
  String serviceName = getServiceName()
  def maxFiles = 9
  try {
    def filesList = Arrays.asList(sh(
      script: """|#!/bin/bash
                 |set +ex
                 |docker exec ${serviceName}-ci git diff --name-only
                 |""".stripMargin(),
      returnStdout: true
    ).split(/\n/))
    def changeSummary = sh(
      script: """|#!/bin/bash
                 |set +ex
                 |docker exec ${serviceName}-ci git diff --shortstat
                 |""".stripMargin(),
      returnStdout: true
    ).trim()
    if (filesList.size() > maxFiles) {
      filesList = filesList.take(maxFiles) + ["..."]
    }
    def placeholder = """|```
                         |${filesList.join("\n")}
                         |${changeSummary}
                         |```""".stripMargin()

    new Github().commentOnPrBySha(
      gitUrl, sha,
      """|:x: Looks like you missed running some pre-commit hooks on your PR.
         |
         |Please ensure pre-commit hooks are set up properly
         |(see [README.md](../blob/${sha}/README.md#setup-local-environment)),
         |and run pre-commit hooks on all files to fix them in place,
         |`pre-commit run --all-files`:
         |
         |SUMMARY-PLACEHOLDER
         |
         |Then, create and push a commit with those changes so pre-commit hooks pass in CI.
         |""" \
          .stripMargin() \
          .split(/\n{2,}/) \
          .collect { it.replace("\n", " ") } \
          .join("\n\n") \
          .replace("SUMMARY-PLACEHOLDER", placeholder)
    )
  } catch (e) {
    println "Failed commenting on ${gitUrl}:${sha} that pre-commit hooks failed"
  }
}


/**
 * Run the pre-commit checks (excluding mypy/flake8)
 */
def runHooks() {
  String serviceName = getServiceName()
  new Github().doClosureWithStatus({
    try {
      sh """|#!/bin/bash
            |set -eoxo pipefail
            |docker exec ${serviceName}-ci git reset --hard
            |docker exec ${serviceName}-ci make test-install-hooks PRE_COMMIT_HOME=/home
            |docker exec ${serviceName}-ci make test-hooks PRE_COMMIT_HOME=/home SKIP=flake8,mypy HOOKS_ADDOPTS="--show-diff-on-failure"
            |""".stripMargin()
    } catch (e) {
      // ignore if step was aborted
      if (!(e instanceof FlowInterruptedException)) {
        commentHooksFailed()
      }
      throw e
    } finally {
      sh """|#!/bin/bash
            |set -eox
            |docker exec ${serviceName}-ci touch pre-commit.log
            |docker cp ${serviceName}-ci:/home/pre-commit.log pre-commit-error.log
            |""".stripMargin()
      archiveArtifacts artifacts: "pre-commit-error.log"
    }
  }, gitUrl, sha, "Hooks", "${BUILD_URL}console")
}

/**
 * Migrate a Microservice.
 */
def migrateService(Map optArgs = [:], String gitUrl, String sha, String env) {
  Map o = [
    k8sCredFileCredentialId: "K8S_CONFIG_${env.toUpperCase()}_NEW",
    k8sCluster: env,
    k8sNamespace: gitUrl,
  ] << envToOptArgs(gitUrl, env) << optArgs

  String tag = sha

  try {
    tag = getImmutableReleaseSemverTag(sha)
  } catch (err) {
    println "Sha does not have an associated semver tag. Using SHA as tag."
  }

  deployHelm(tag, 'payment-service-migration', env)
  getMigrationJobLog(env)
  if (env == 'staging') {
    deployBlockingPulse(gitUrl, sha, env)
  }
}

/**
 * Deploy a Microservice.
 */
def deployService(Map optArgs = [:], String gitUrl, String sha, String env) {
  Map o = [
    k8sCredFileCredentialId: "K8S_CONFIG_${env.toUpperCase()}_NEW",
    k8sCluster: env,
    k8sNamespace: gitUrl,
  ] << envToOptArgs(gitUrl, env) << optArgs

  String tag = sha

  try {
    tag = getImmutableReleaseSemverTag(sha)
  } catch (err) {
    println "Sha does not have an associated semver tag. Using SHA as tag."
  }

  installTerraform()
  sshagent (credentials: ['DDGHMACHINEUSER_PRIVATE_KEY']) { // Required for terraform to git clone
    withCredentials([file(credentialsId: o.k8sCredFileCredentialId, variable: 'k8sCredsFile')]) { // Required for k8s config
      sh """|#!/bin/bash
            |set -ex
            |
            |# Use Terraform to create the namespace when it doesn't exist
            |pushd _infra/namespace/${o.k8sCluster}
            |rm -rf .terraform terraform.*
            |sed 's/_GITREPO_/${o.k8sNamespace}/g' namespace.tf.template > namespace.tf
            |terraform="${WORKSPACE}/_infra/terraform"
            |\${terraform} init
            |\${terraform} plan -out terraform.tfplan \\
            | -var="k8s_config_path=${k8sCredsFile}" \\
            | -var="namespace=${o.k8sNamespace}" \\
            | -var="service_account_namespace=${o.k8sCluster}"
            |\${terraform} apply terraform.tfplan
            |popd
            |
            |# Use Terraform to deploy the service
            |pushd _infra/${o.k8sCluster}
            |rm -rf .terraform terraform.*
            |sed 's/_GITREPO_/${o.k8sNamespace}/g' service.tf.template > service.tf
            |cp -f ${WORKSPACE}/_infra/templates/common.tf common.tf
            |terraform="${WORKSPACE}/_infra/terraform"
            |\${terraform} init
            |\${terraform} plan -out terraform.tfplan \\
            | -var="k8s_config_path=${k8sCredsFile}" \\
            | -var="image_tag=${tag}" \\
            | -var="namespace=${o.k8sNamespace}" \\
            | -var="service_name=${getServiceName()}"
            |\${terraform} apply terraform.tfplan
            |popd
            |""".stripMargin()
    }
  }
}

/**
 * Deploy a Microservice using Helm.
 */
def deployHelm(Map optArgs = [:], String tag, String serviceName, String env) {
  Map o = [
          helmCommand: 'upgrade',
          helmFlags: '--install',
          helmChartPath: "_infra/charts/${serviceName}",
          helmValuesFile: "values-${env}.yaml",
          helmRelease: serviceName,
          k8sCredFileCredentialId: "K8S_CONFIG_${env.toUpperCase()}_NEW",
          k8sNamespace: env,
          tillerNamespace: env,
          timeoutSeconds: 600
  ] << serviceNameEnvToOptArgs(serviceName, env) << optArgs
  withCredentials([file(credentialsId: o.k8sCredFileCredentialId, variable: 'k8sCredsFile')]) {
    sh """|#!/bin/bash
      |set -ex
      |
      |# use --wait flag for helm to wait until all pod and services are in "ready" state.
      |# working together with k8s readiness probe to prevent uninitialized pod serving traffic
      |helm="docker run --rm -v ${k8sCredsFile}:/root/.kube/config -v ${WORKSPACE}:/apps alpine/helm:2.10.0"
      |HELM_OPTIONS="${o.helmCommand} ${o.helmRelease} ${o.helmChartPath} \\
      | --values ${o.helmChartPath}/${o.helmValuesFile} --set web.tag=${tag} --set cron.tag=${tag} --set migration.tag=${tag} \\
      | ${o.helmFlags} --tiller-namespace ${o.tillerNamespace} --namespace ${o.k8sNamespace} \\
      | --wait --timeout ${o.timeoutSeconds}"
      |
      |# log manifest to CI/CD
      |\${helm} \${HELM_OPTIONS} --debug --dry-run
      |
      |\${helm} \${HELM_OPTIONS}
      |""".stripMargin()
  }
}

/**
 * Deploy Pulse for a Microservice.
 */
def deployPulse(Map optArgs = [:], String gitUrl, String sha, String env) {
  Map o = [
    k8sCluster: env,
    k8sNamespace: gitUrl,
    pulseVersion: '2.1',
    pulseDoorctlVersion: 'v0.0.119',
    pulseRootDir: 'pulse'
  ] << envToOptArgs(gitUrl, env) << optArgs

  String PULSE_VERSION = o.pulseVersion
  String SERVICE_NAME = getServiceName()
  String KUBERNETES_CLUSTER = o.k8sCluster
  String KUBERNETES_NAMESPACE = o.k8sCluster // Use o.k8sNamespace once Pulse can be deployed to the service namespace
  String DOORCTL_VERSION = o.pulseDoorctlVersion
  String PULSE_DIR = o.pulseRootDir

  sshagent(credentials: ['DDGHMACHINEUSER_PRIVATE_KEY']) {
    // install doorctl and grab its executable path
    String doorctlPath = new Doorctl().installIntoWorkspace(DOORCTL_VERSION)
    // deploy Pulse
    cleanPulseImage()
    new Pulse().deploy(PULSE_VERSION, SERVICE_NAME, KUBERNETES_CLUSTER, doorctlPath, PULSE_DIR, KUBERNETES_NAMESPACE, null, sha)
  }
}

/**
 * Deploy Blocking Pulse for a Microservice.
 */
def deployBlockingPulse(Map optArgs = [:], String gitUrl, String sha, String env) {
  Map o = [
    k8sCluster: env,
    k8sNamespace: gitUrl,
    pulseVersion: '2.1',
    pulseDoorctlVersion: 'v0.0.119',
    pulseRootDir: 'pulse'
  ] << envToOptArgs(gitUrl, env) << optArgs

  String PULSE_VERSION = o.pulseVersion
  String SERVICE_NAME = getServiceName()
  String SERVICE_SHA = sha
  String KUBERNETES_CLUSTER = o.k8sCluster
  String KUBERNETES_NAMESPACE = o.k8sCluster // Use o.k8sNamespace once Pulse can be deployed to the service namespace
  String DOORCTL_VERSION = o.pulseDoorctlVersion
  String PULSE_DIR = o.pulseRootDir
  Integer TIMEOUT_S = 360
  Integer SLEEP_S = 5
  sshagent(credentials: ['DDGHMACHINEUSER_PRIVATE_KEY']) {
    // install doorctl and grab its executable path
    String doorctlPath = new Doorctl().installIntoWorkspace(DOORCTL_VERSION)
    cleanPulseImage()
    // deploy Pulse
    new Pulse().blockingDeploy(PULSE_VERSION, SERVICE_NAME, SERVICE_SHA, KUBERNETES_CLUSTER, doorctlPath, PULSE_DIR, TIMEOUT_S, SLEEP_S, KUBERNETES_NAMESPACE)
  }
}

def cleanPulseImage() {
  sh """|#!/bin/bash
        |set -x
        |docker rmi -f ddartifacts-docker.jfrog.io/pulse-base || true
        |""".stripMargin()
}

/**
 * Return the name of the repo taken from the end of the Git URL.
 * Throw an assertion error if the Git Repo name is not valid for use as a kubernetes namespace.
 * It must be less than 64 alphanumeric characters and may contain dashes.
 */
def getGitRepoName(String gitUrl) {
  String gitRepo = gitUrl.tokenize('/').last().split("\\.git")[0]
  assert gitRepo.length() < 64
  assert gitRepo ==~ /^[a-z0-9]([-a-z0-9]*[a-z0-9])?$/ :
      "The Git Repo name is not valid for use as a kubernetes namespace. " +
      "It must be less than 64 alphanumeric characters and may contain dashes"
  return gitRepo
}

/**
 * Given an environment name like 'sandbox1', 'staging', and 'production',
 * resolve the optional arguments that vary per environment.
 */
def envToOptArgs(String gitUrl, String env) {
  String gitRepo = getGitRepoName(gitUrl)
  if (env ==~ /^sandbox([0-9]|1[0-5])/) { // sandbox0 - sandbox15
    return [
      k8sCredFileCredentialId: 'K8S_CONFIG_STAGING_NEW',
      k8sCluster: 'staging',
      k8sNamespace: gitRepo,
    ]
  } else if (env == 'staging') {
    return [
      k8sCredFileCredentialId: 'K8S_CONFIG_STAGING_NEW',
      k8sCluster: 'staging',
      k8sNamespace: gitRepo,
    ]
  } else if (env == 'prod' || env == 'production') {
    return [
      k8sCredFileCredentialId: 'K8S_CONFIG_PROD_NEW',
      k8sCluster: 'prod',
      k8sNamespace: gitRepo,
    ]
  } else {
    error("Unknown env value of '${env}' passed.")
  }
}

/**
 * Given a service name and environment name like 'sandbox1', 'staging', and 'production',
 * resolve the optional arguments that vary per environment.
 */
def serviceNameEnvToOptArgs(String serviceName, String env) {
  if (env ==~ /^sandbox([0-9]|1[0-5])/) { // sandbox0 - sandbox15
    return [
            helmFlags: '--install --force',
            helmValuesFile: "values-${env}.yaml",
            helmRelease: "${serviceName}-${env}",
            k8sCredFileCredentialId: 'K8S_CONFIG_STAGING_NEW',
            k8sNamespace: 'staging',
            tillerNamespace: 'staging'
    ]
  } else if (env == 'staging') {
    return [
            helmFlags: '--install --force',
            helmValuesFile: 'values-staging.yaml',
            helmRelease: serviceName,
            k8sCredFileCredentialId: 'K8S_CONFIG_STAGING_NEW',
            k8sNamespace: 'staging',
            tillerNamespace: 'staging'
    ]
  } else if (env == 'prod' || env == 'production') {
    return [
            helmFlags: '--install',
            helmValuesFile: 'values-prod.yaml',
            helmRelease: serviceName,
            k8sCredFileCredentialId: 'K8S_CONFIG_PROD_NEW',
            k8sNamespace: 'prod',
            tillerNamespace: 'prod'
    ]
  } else {
    error("Unknown env value of '${env}' passed.")
  }
}

/**
 * Remove the CI containers and images
 */
def dockerClean() {
  sh """|#!/bin/bash
        |set -x
        |docker ps -a -q | xargs --no-run-if-empty docker rm -f || true
        |make remove-docker-images
        |""".stripMargin()
}

/**
 * Prompt the user to decide if we can deploy to production.
 * The user has 10 minutes to choose between Proceed or Abort.
 * If Proceed, then we should proceed. If Abort or Timed-out,
 * then we should cleanly skip the rest of the steps in the
 * pipeline without failing the pipeline.
 *
 * @return True if we can deploy to prod. False, otherwise.
 */
def inputCanDeployToProd(String message = 'Deploy to production') {
  boolean canDeployToProd = false
  try {
    timeout(time: 10, unit: 'MINUTES') {
      input(id: 'userInput', message: message)
      canDeployToProd = true
    }
  } catch (err) {
    println "Timed out or Aborted! Will not deploy to production."
    println err
  }
  return canDeployToProd
}

/**
 * Get service migration job logs
 */
def getMigrationJobLog(String env) {
    println 'Query for splunk:'
    println "index=${env} kubernetes.labels.job-name=payment-service-migration-job | table log | reverse"
    withCredentials([file(credentialsId: "K8S_CONFIG_${env.toUpperCase()}_NEW", variable: 'k8sCredsFile')]) {
      sh """|#!/bin/bash
            |set -ex
            |export KUBECONFIG=$k8sCredsFile
            |# Find pod name so that we can manage it
            |POD_NAME=''
            |for i in 1 2 4 8; do
            |  POD_NAME=\$(kubectl get pods -n ${env} --selector='job-name=payment-service-migration-job' -o name)
            |  if [[ "\${POD_NAME}" != "" ]]; then
            |    echo "Found pod \${POD_NAME}"
            |    break
            |  fi
            |  echo "Did not find pod, waiting for \${i} seconds"
            |  sleep \$i
            |done
            |if [[ "\${POD_NAME}" == "" ]]; then
            |  echo "Failed to find pod for payment-service-migration-job"
            |  exit 1
            |fi
            |
            |# Wait for job to be completed.
            |kubectl wait --for=condition=complete --timeout=20m job.batch/payment-service-migration-job -n ${env}
            |# Pod is completed, gather logs from it
            |kubectl logs -n ${env} \$POD_NAME
            |kubectl delete job payment-service-migration-job -n ${env}
            |""".stripMargin()
      }
}

/**
 * Prompt the user to decide if we can deploy the pipeline.
 * The user has 2 minutes to choose between Proceed or Abort.
 * If Proceed, then we should proceed. If Abort or Timed-out,
 * then we should cleanly skip the rest of the steps in the
 * pipeline without failing the pipeline.
 *
 * @return True if we can deploy the pipeline. False, otherwise.
 */
def inputDeployPipeline(String message = 'Continue Deploying Pipeline') {
  boolean canDeployPipeline = false
  try {
    timeout(time: 2, unit: 'MINUTES') {
      input(id: 'userInput', message: message)
      canDeployPipeline = true
    }
  } catch (err) {
    println "Timed out or Aborted! Will not deploy the pipeline."
    println err
  }
  return canDeployPipeline
}

/**
 * Run unit tests within a docker-compose container.
 */
def runTests(String stageName, String gitUrl, String sha) {
  return // Not necessary
  new Github().doClosureWithStatus({
    withCredentials([
      string(credentialsId: 'ARTIFACTORY_MACHINE_USER_NAME', variable: 'ARTIFACTORY_USERNAME'),
      string(credentialsId: 'ARTIFACTORY_MACHINE_USER_PASS', variable: 'ARTIFACTORY_PASSWORD'),
      string(credentialsId: 'PIP_EXTRA_INDEX_URL', variable: 'PIP_EXTRA_INDEX_URL')
    ]) {
      sh """|#!/bin/bash
            |set -x
            |docker-compose run --rm web make test
            |""".stripMargin()
    }
  }, gitUrl, sha, stageName, "${BUILD_URL}testReport")
}

return this
