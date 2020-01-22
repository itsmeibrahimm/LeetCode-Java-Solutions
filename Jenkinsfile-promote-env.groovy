/**
 * Expected inputs:
 * ----------------
 * params['SHA']                - Sha to promote
 * params['GITHUB_REPOSITORY']  - GitHub ssh url of repository (git://....)
 * params['JSON']               - Extensible json doc with extra information
 * params['REF']                - The reference (tag, branch, or sha) from the ddops command line
 * params['ENV']                - The environment from the ddops command line
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
    stage('Deploy to env') {
      steps {
        script {
          common = load "${WORKSPACE}/Jenkinsfile-common.groovy"
          deployService(params['GITHUB_REPOSITORY'], params['SHA'], params['ENV'], common.getServiceName(), terraformVersion: '0.12.7')
        }
      }
    }
    stage('Deploy Blocking Pulse to env') {
      steps {
        script {
          common = load "${WORKSPACE}/Jenkinsfile-common.groovy"
          common.deployBlockingPulse(params['GITHUB_REPOSITORY'], params['SHA'], params['ENV'])
        }
      }
    }
  }
  post {
    success {
      sendSlackMessage common.getSlackChannel(), "Successful promote of ${common.getServiceName()}:${params['REF']} to ${params['ENV']}: <${BUILD_URL}|${env.JOB_NAME} [${env.BUILD_NUMBER}]>"
    }
    failure {
      sendSlackMessage common.getSlackChannel(), "Promote failed for ${common.getServiceName()}:${params['REF']} to ${params['ENV']}: <${BUILD_URL}|${env.JOB_NAME} [${env.BUILD_NUMBER}]>"
    }
  }
}
