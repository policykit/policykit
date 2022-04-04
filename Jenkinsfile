pipeline {
    agent any

    environment {
        service="policykiy"
    }

    stages {
        stage('Test') {
            steps {
                script {
                    sh """
                    echo "Creating a new stage"
                    """
                }
            }
        }

        stage('Build Application') {
            steps {
                script {
                    sh """
                    docker-compose build
                    """
                }
            }
        }

        stage('Running Unit Test Cases') {
            steps {
                script {
                    sh """
                    echo "Unit test cases"
                    """
                }
            }
        }

        stage('Push container to Artifactory') {
            steps {
                script {
                    sh """
                    echo "Pushing containers to artifactory"
                    """
                }
            }
        }

        stage('Delete Docker Containers from Host') {
            steps {
                script {
                    sh """
                    echo "Deleting docker images"
                    """
                }
            }
        }

        stage('Clean Workspace') {
            steps {
                cleanWs()
            }
        }
    }
}