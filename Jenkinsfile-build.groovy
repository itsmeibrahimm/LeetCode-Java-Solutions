@Library('common-pipelines@10.17.0') _

/**
 * Expected inputs:
 * ----------------
 * params['SHA']                - Sha to build
 * params['GITHUB_REPOSITORY']  - GitHub ssh url of repository (git://....)
 * params['JSON']               - Extensible json doc with extra information
 */

pipeline {
  options {
    timestamps()
    skipStagesAfterUnstable()
    timeout(time: 30, unit: 'MINUTES')
  }
  agent {
    label 'universal'
  }
  stages {
    stage('Docker Build') {
      steps {
        script {
          common = load "${WORKSPACE}/Jenkinsfile-common.groovy"
          common.dockerBuild(params['GITHUB_REPOSITORY'], params['SHA'])
        }
      }
    }
    stage('Run CI container') {
      steps {
        script {
          common = load "${WORKSPACE}/Jenkinsfile-common.groovy"
          common.runCIcontainer(params['GITHUB_REPOSITORY'], params['SHA'], env.tag)
        }
      }
    }
    stage('Linting') {
      steps {
        script {
          common = load "${WORKSPACE}/Jenkinsfile-common.groovy"
          common.runLinter()
        }
      }
    }
    stage('Typing') {
      steps {
        script {
          common = load "${WORKSPACE}/Jenkinsfile-common.groovy"
          common.runTyping()
        }
      }
    }
    stage('Unit Tests') {
      steps {
        script {
          common = load "${WORKSPACE}/Jenkinsfile-common.groovy"
          common.runUnitTests()
        }
      }
    }
    stage('Integration Tests') {
      steps {
        script {
          common = load "${WORKSPACE}/Jenkinsfile-common.groovy"
          common.runIntegrationTests()
        }
      }
    }
    stage('Pulse tests') {
      steps {
        script {
          common = load "${WORKSPACE}/Jenkinsfile-common.groovy"
          common.runPulseTests()
        }
      }
    }
  }
  post {
    always {
      script {
        common.dockerClean()
      }
    }
    success {
      script {
        tag = getImmutableReleaseSemverTag(params['SHA'])
      }
      sendSlackMessage common.getSlackChannel(), "Successful build of ${common.getServiceName()} to ${tag}: <${BUILD_URL}|${env.JOB_NAME} [${env.BUILD_NUMBER}]>"
    }
    failure {
      script {
        tag = getImmutableReleaseSemverTag(params['SHA'])
      }
      sendSlackMessage common.getSlackChannel(), "Build failed for ${common.getServiceName()} to ${tag}: <${BUILD_URL}|${env.JOB_NAME} [${env.BUILD_NUMBER}]>"
    }
  }
}
