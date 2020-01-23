/**
 * Expected inputs:
 * ----------------
 * params['SHA']                - SHA containing the migrations that should be run
 * params['GITHUB_REPOSITORY']  - GitHub ssh url of repository (git://....)
 * params['JSON']               - Extensible json doc with extra information
 * params['REF']                - The reference (tag, branch, or sha) from the ddops command line
 * params['ENV']                - The environment from the ddops command line
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
    stage('Migrate env') {
      steps {
        script {
          common = load "${WORKSPACE}/Jenkinsfile-common.groovy"
          common.migrateService(params['GITHUB_REPOSITORY'], params['SHA'], params['ENV'])
        }
      }
    }
  }
  post {
    success {
      sendSlackMessage common.getSlackChannel(), "Successful migrate of ${common.getServiceName()}:${params['REF']} to ${params['ENV']}: <${BUILD_URL}|${env.JOB_NAME} [${env.BUILD_NUMBER}]>"
    }
    failure {
      sendSlackMessage common.getSlackChannel(), "Migrate failed for ${common.getServiceName()}:${params['REF']} to ${params['ENV']}: <${BUILD_URL}|${env.JOB_NAME} [${env.BUILD_NUMBER}]>"
    }
  }
}
