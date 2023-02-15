pipeline {
    agent any

    stages {
        stage("Testing PR") {
            when { anyOf { branch 'master' } }
            steps {
                script {
                    sh """
                    echo "Testing Phase!!!"
                    ls
                    """
                }
            }
        }
    }
}