pipeline {
    agent any

    stages {
        stage("Creating Virtual Environment") {
            steps {
                script {
                    sh """
                    env
                    virtualenv venv
                    """
                }
            }
        }

        stage("Installing Requirements") {
            steps {
                script {
                    sh """
                    . venv/bin/activate
                    cd policykit
                    pip install -U pip setuptools
                    pip install -r requirements.txt
                    """
                }
            }
        }

        stage("Running Unit Test") {
            steps {
                script {
                    sh """
                    . venv/bin/activate
                    cd policykit
                    python manage.py test
                    """
                }
            }
        }

        stage("Build Docker Image"){
            steps {
                script {
                    """
                    docker build --no-cache -t metagovpolicykit/policykit:${BUILD_NUMBER} .
                    """
                }
            }
        }

        stage("Push Image to Dockerhub"){
            steps {
                script {
                    """
                    docker login --username metagovpolicykit --password 993250da-52ef-4757-9b41-162d779b0a90

                    echo "Publishing image to dockerhub..."
                    docker push metagovpolicykit/policykit:${BUILD_NUMBER}
                    """
                }
            }
        }

        stage("Push Image to Dockerhub"){
            steps {
                script {
                    """
                    docker login --username metagovpolicykit --password 993250da-52ef-4757-9b41-162d779b0a90

                    echo "Publishing image to dockerhub..."
                    docker push metagovpolicykit/policykit:${BUILD_NUMBER}
                    """
                }
            }
        }

        stage("Deploy Image to Prodcution"){
            steps {
                script {
                    """
                    cd /home/ubuntu/policykit
                    docker-compose stop policykit_app
                    docker-compose rm --force policykit_app
                    policykit_tag=${BUILD_NUMBER} docker-compose up -d --force-recreate --no-deps policykit_app
                    docker system prune --all --force
                    """
                }
            }
        }

        stage("Docker Cleanup"){
            steps {
                script {
                    """
                    docker system prune --all --force
                    """
                }
            }
        }
    }

     post {
        always {
            script {
                owner_repo = GIT_URL.replaceAll("https://github.com/", "").replaceAll(".git", "")

                if (env.CHANGE_URL) {
                    commit_type = "PR"
                    html_url = env.CHANGE_URL
                    pr_api = CHANGE_URL.replaceAll("https://github.com/", "https://api.github.com/repos/").replaceAll("pull", "pulls")
                    def commit_sha = sh(script: "curl -H 'Accept: application/vnd.github.v3+json' ${pr_api} | jq -r .base.sha", returnStdout: true).trim()
                    api_url = "https://api.github.com/repos/${owner_repo}/commits/${commit_sha}"
                }
                else {
                    commit_type = "Commit"
                    html_url = "https://github.com/${owner_repo}/commit/${GIT_COMMIT}"
                    api_url = "https://api.github.com/repos/${owner_repo}/commits/${GIT_COMMIT}"
                }

                def commit_metadata = sh(script: "curl -H 'Accept: application/vnd.github.v3+json' ${api_url} | jq .commit", returnStdout: true).trim()
                def commit_metadata_json = readJSON text: commit_metadata

                commit_message = "${commit_metadata_json.message}"
                committer_name  = "${commit_metadata_json.committer.name}"
                committer_email  = "${commit_metadata_json.committer.email}"
            }
        }

        success {
            script {
                 slackSend botUser: true,
                           color: '#00ff00',
                           message: "Type: " + commit_type +
                                    "\n User: " + committer_name +
                                    "\n Branch: " + GIT_BRANCH +
                                    "\n Message: " + commit_message +
                                    "\n Build Status: Passed :tada: :tada: :tada:" +
                                    "\n Build Url: " + BUILD_URL +
                                    "\n Github Url: " + html_url
            }
        }

        failure {
            script {
                slackSend botUser: true,
                      color: '#ff0000',
                      message: "Type: " + commit_type +
                               "\n User: " + committer_name +
                               "\n Branch: " + GIT_BRANCH +
                               "\n Message: " + commit_message +
                               "\n Build Status: Failed :disappointed: :disappointed: :disappointed:" +
                               "\n Build Url: " + BUILD_URL +
                               "\n Github Url: " + html_url
            }
        }
    }
}