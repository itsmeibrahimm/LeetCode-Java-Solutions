@Library('common-pipelines@11.12.0') _

/**
 * Expected inputs:
 * ----------------
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
    stage('Bounce prod') {
      steps {
        script {
          common = load "${WORKSPACE}/Jenkinsfile-common.groovy"
          common.bounceService(params['GITHUB_REPOSITORY'], params['SHA'], 'prod', 'web')
          common.bounceService(params['GITHUB_REPOSITORY'], params['SHA'], 'prod', 'webhook')
        }
      }
      post {
        success {
          sendSlackMessage 'eng-deploy-manifest', "Successful bounce of ${common.getServiceName()}: <${BUILD_URL}|${env.JOB_NAME} [${env.BUILD_NUMBER}]>"
        }
        failure {
          sendSlackMessage 'eng-deploy-manifest', "Bounce failed for ${common.getServiceName()}: <${BUILD_URL}|${env.JOB_NAME} [${env.BUILD_NUMBER}]>"
        }
      }
    }
  }
  post {
    always {
      deleteDir()
    }
    success {
      sendSlackMessage common.getSlackChannel(), "Successful bounce of ${common.getServiceName()}: <${BUILD_URL}|${env.JOB_NAME} [${env.BUILD_NUMBER}]>"
    }
    failure {
      sendSlackMessage common.getSlackChannel(), "Bounce failed for ${common.getServiceName()}: <${BUILD_URL}|${env.JOB_NAME} [${env.BUILD_NUMBER}]>"
    }
  }
}
