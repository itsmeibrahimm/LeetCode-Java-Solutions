@Library('common-pipelines@10.16.0') _

import groovy.transform.Field
/**
 * Expected inputs:
 * ----------------
 * params['SHA']                - Sha to build
 * params['GITHUB_REPOSITORY']  - GitHub ssh url of repository (git://....)
 * params['JSON']               - Extensible json doc with extra information
 */

@Field
def runningStage = "Not Started"

pipeline {
  agent {
    label 'universal'
  }
  stages {
    stage('Startup') {
      steps {
        script {
          runningStage = env.STAGE_NAME
        }
        artifactoryLogin()
        script {
          /**
           * Beware: Github does not offer a way for us to "protect" git tags. Any
           * developer can "force push" tags causing chaos and GitHub offers no way
           * for us to prevent that.
           *
           * Ddops maintains it's own immutable database of sha/semvertag bindings and
           * the getImmutableReleaseSemverTag() function will retrieve the semver tag
           * value that was originally registered with the params['SHA'].
           *
           * If you decide to access the original semver value, please do not use it for
           * anything important. In other words your "1.0.0" tag might have been "force
           * pushed" around. You could unknowingly end up building/deploying (etc) a
           * version of that code that doesn't match the params['SHA'] value.
           */
          env.tag = getImmutableReleaseSemverTag(params['SHA'])
          common = load "${WORKSPACE}/Jenkinsfile-common.groovy"
        }
      }
    }
    stage('Docker Build Tag Push - [NoRelease]') {
      steps {
        script {
          runningStage = env.STAGE_NAME
        }
        script {
          common.buildTagPushNoRelease(params['GITHUB_REPOSITORY'], params['SHA'], params['BRANCH_NAME'], common.getServiceName())
        }
      }
    }
    stage('Docker Tag Push - [Release]') {
      steps {
        script {
          runningStage = env.STAGE_NAME
        }
        script {
          common.tagPushRelease(env.tag, params['SHA'])
        }
      }
    }
    stage('Run CI container') {
      steps {
        script {
          runningStage = env.STAGE_NAME
        }
        script {
          common.runCIcontainer(common.getServiceName(), env.tag)
        }
      }
    }
    stage('Unit Tests') {
      steps {
        script {
          runningStage = env.STAGE_NAME
        }
        script {
          common.runUnitTests(common.getServiceName())
        }
      }
    }
    stage('Integration Tests') {
      steps {
        script {
          runningStage = env.STAGE_NAME
        }
        script {
          common.runIntegrationTests(common.getServiceName())
        }
      }
    }
    stage('Pulse tests') {
      steps {
        script {
          runningStage = env.STAGE_NAME
        }
        script {
          common.runPulseTests(common.getServiceName())
        }
      }
    }
    stage('Linting') {
      steps {
        script {
          runningStage = env.STAGE_NAME
        }
        script {
          common.runLinter(common.getServiceName())
        }
      }
    }
    stage('Typing') {
      steps {
        script {
          runningStage = env.STAGE_NAME
        }
        script {
          common.runTyping(common.getServiceName())
        }
      }
    }
  }
  post {
    always {
      script {
        common.removeAllContainers()
      }
    }
    failure {
      script {
        common.notifySlackChannelDeploymentStatus(runningStage, params['SHA'], "${env.BUILD_NUMBER}", "failure", true)
      }
    }
    success {
      script {
        common.notifySlackChannelDeploymentStatus("Successful Build Release", params['SHA'], "${env.BUILD_NUMBER}", "success", false)
      }
    }
  }
}
