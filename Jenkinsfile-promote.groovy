/**
 * Expected inputs:
 * ----------------
 * params['SHA']                - Sha to promote
 * params['GITHUB_REPOSITORY']  - GitHub ssh url of repository (git://....)
 * params['JSON']               - Extensible json doc with extra information
 */

pipeline {
  options {
    timestamps()
    skipStagesAfterUnstable()
    timeout(time: 60, unit: 'MINUTES')
  }
  agent {
    label 'universal'
  }
  stages {
    stage('Deploy to prod') {
      steps {
        script {
          common = load "${WORKSPACE}/Jenkinsfile-common.groovy"
          deployService(params['GITHUB_REPOSITORY'], params['SHA'], 'prod', common.getServiceName(), terraformVersion: '0.12.7')
        }
      }
      post {
        success {
          script {
            tag = getImmutableReleaseSemverTag(params['SHA'])
          }
          sendSlackMessage 'eng-deploy-manifest', "Successful promote of ${common.getServiceName()} to ${tag}: <${BUILD_URL}|${env.JOB_NAME} [${env.BUILD_NUMBER}]>"
        }
        failure {
          script {
            tag = getImmutableReleaseSemverTag(params['SHA'])
          }
          sendSlackMessage 'eng-deploy-manifest', "Promote failed for ${common.getServiceName()} to ${tag}: <${BUILD_URL}|${env.JOB_NAME} [${env.BUILD_NUMBER}]>"
        }
      }
    }
    stage('Deploy Pulse to prod') {
      steps {
        script {
          common = load "${WORKSPACE}/Jenkinsfile-common.groovy"
          common.deployPulse(params['GITHUB_REPOSITORY'], params['SHA'], 'prod')
        }
      }
    }
  }
  post {
    success {
      script {
        tag = getImmutableReleaseSemverTag(params['SHA'])
      }
      sendSlackMessage common.getSlackChannel(), "Successful promote of ${common.getServiceName()} to ${tag}: <${BUILD_URL}|${env.JOB_NAME} [${env.BUILD_NUMBER}]>"
    }
    failure {
      script {
        tag = getImmutableReleaseSemverTag(params['SHA'])
      }
      sendSlackMessage common.getSlackChannel(), "Promote failed for ${common.getServiceName()} to ${tag}: <${BUILD_URL}|${env.JOB_NAME} [${env.BUILD_NUMBER}]>"
    }
  }
}
