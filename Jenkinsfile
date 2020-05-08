pipeline {
  agent any
  triggers {
    cron('H 0 * * *')
  }
    
  parameters {
    string(defaultValue: "", description: 'Jira Query', name: 'jiraQuery')
  }

  environment {
    JIRA_QUERY = "${params.jiraQuery}"
  }

  stages {
    stage('Create Feature Files') {
        agent { 
            docker { 
                image 'python:3.8.2'
            }
        }
        steps {
            sh 'python get_features.py' 
        }
        post {
            success {
                sh 'rm features.zip || true'
                zip zipFile: 'features.zip', archive: true, dir: 'features'
                archiveArtifacts artifacts: 'features.zip', fingerprint: true
            }
        }
    } 
    post {
      cleanup { 
        cleanWs()
        deleteDir()
    }
  }
}
}