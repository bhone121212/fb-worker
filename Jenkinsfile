pipeline {
    agent any

    environment {
        IMAGE_NAME = 'bhonebhone/fb-worker'
        K8S_NAMESPACE = "fb-crawler-apps"
        VERSION_FILE = 'version.txt'
    }

    stages {
        stage('Checkout Code') {
            steps {
                checkout scm
            }
        }

        // stage('Check Merge Condition') {
        //     when {
        //         expression {
        //             def msg = sh(script: "git log -1 --pretty=%B", returnStdout: true).trim()
        //             return env.BRANCH_NAME == 'main' && msg.contains('from bhone121212/dev')
        //         }
        //     }
        //     steps {
        //         echo "✅ Proceeding: This is a merge from 'dev' to 'main'"
        //     }
        // }

        // stage('Skip Pipeline for Non-Merges') {
        //     when {
        //         not {
        //             expression {
        //                 def msg = sh(script: "git log -1 --pretty=%B", returnStdout: true).trim()
        //                 return env.BRANCH_NAME == 'main' && msg.contains('from bhone121212/dev')
        //             }
        //         }
        //     }
        //     steps {
        //         echo "🚫 Skipping pipeline. Not a merge from dev to main."
        //         script {
        //             currentBuild.result = 'NOT_BUILT'
        //             error("❌ Build aborted: Not a valid dev → main merge.")
        //         }
        //     }
        // }
        // stage('Check Merge Condition') {
        //     when {
        //         expression {
        //             def branch = sh(script: "git rev-parse --abbrev-ref HEAD", returnStdout: true).trim()
        //             def msg = sh(script: "git log -1 --pretty=%B", returnStdout: true).trim()
        //             echo "🔍 Branch: ${branch}"
        //             echo "🔍 Commit message: ${msg}"
        //             return branch == 'main' && msg.contains('Merge pull request') && msg.contains('bhone121212/dev')
        //         }
        //     }
        //     steps {
        //         echo "✅ Proceeding: This is a merge from 'dev' to 'main'"
        //     }
        // }

        // stage('Skip Pipeline for Non-Merges') {
        //     when {
        //         not {
        //             expression {
        //                 def branch = sh(script: "git rev-parse --abbrev-ref HEAD", returnStdout: true).trim()
        //                 def msg = sh(script: "git log -1 --pretty=%B", returnStdout: true).trim()
        //                 echo "🔍 Branch: ${branch}"
        //                 echo "🔍 Commit message: ${msg}"
        //                 return branch == 'main' && msg.contains('Merge pull request') && msg.contains('bhone121212/dev')
        //             }
        //         }
        //     }
        //     steps {
        //         echo "🚫 Skipping pipeline. Not a merge from dev to main."
        //         script {
        //             currentBuild.result = 'NOT_BUILT'
        //             error("❌ Build aborted: Not a valid dev → main merge.")
        //         }
        //     }
        // }
        stage('Check Merge Condition') {
            steps {
                script {
                    def branch = sh(script: "git branch -r --contains HEAD | grep origin/main || true", returnStdout: true).trim()
                    def msg = sh(script: "git log -1 --pretty=%B", returnStdout: true).trim()
                    echo "🔍 Branch: ${branch}"
                    echo "🔍 Commit message: ${msg}"

                    if (branch.contains("origin/main") && msg.contains("bhone121212/dev")) {
                        echo "✅ This is a merge from 'dev' to 'main'. Proceeding..."
                    } else {
                        echo "🚫 Not a merge from dev to main. Aborting pipeline."
                        currentBuild.result = 'NOT_BUILT'
                        error("❌ Build skipped: Not a dev → main merge.")
                    }
                }
            }
        }




        stage('Set Image Tag') {
            steps {
                script {
                    def version = 0
                    if (fileExists(VERSION_FILE)) {
                        version = readFile(VERSION_FILE).trim().toInteger()
                    }
                    version++
                    writeFile file: VERSION_FILE, text: "$version"
                    env.IMAGE_TAG = "v${version}"
                    env.FULL_IMAGE = "${IMAGE_NAME}:${env.IMAGE_TAG}"
                    echo "📦 New image version: ${env.IMAGE_TAG}"
                }
            }
        }

        stage('Run Tests') {
            steps {
                echo '🔎 Skipping tests - handled in container if needed'
            }
        }

        stage('Build and Push Image (Buildah)') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'dockerhub-cred', usernameVariable: 'REG_USER', passwordVariable: 'REG_PASS')]) {
                    script {
                        sh 'echo "$REG_PASS" | sudo -S buildah login -u "$REG_USER" --password-stdin docker.io'
                        sh "sudo buildah bud -t $FULL_IMAGE ."
                        sh "sudo buildah push $FULL_IMAGE"
                    }
                }
            }
        }

        // stage('Clean Up Old Images') {
        //     steps {
        //         script {
        //             sh '''
        //                 echo "🧹 Cleaning up old images for $IMAGE_NAME, keeping only the latest 5"

        //                 KEEP_IDS=$(buildah images --format "{{.CreatedAt}} {{.ID}} {{.Repository}}:{{.Tag}}" \
        //                     | grep "$IMAGE_NAME" \
        //                     | sort -r \
        //                     | head -n 5 \
        //                     | awk '{print $2}')

        //                 echo "🆕 Keeping these image IDs:"
        //                 echo "$KEEP_IDS"

        //                 ALL_IDS=$(buildah images --format "{{.ID}} {{.Repository}}" | grep "$IMAGE_NAME" | awk '{print $1}')

        //                 for id in $ALL_IDS; do
        //                     if ! echo "$KEEP_IDS" | grep -q "$id"; then
        //                         echo "🗑️ Deleting old image: $id"
        //                         buildah rmi -f "$id" || true
        //                     fi
        //                 done
        //             '''
        //         }
        //     }
        // }
        // stage('Clean Up Old Images') {
        //     steps {
        //         script {
        //             sh '''#!/bin/bash
        //                 set -e
        //                 export BUILDAH_ISOLATION=chroot

        //                 IMAGE_NAME="localhost/bhonebhone/fb-api"
        //                 echo "🧹 Cleaning up old images for $IMAGE_NAME, keeping only the latest 5"

        //                 jq_filter=$(cat <<EOF
        // .[] | select(.Name == "$IMAGE_NAME") | "\\(.CreatedAt) \\(.Id)"
        // EOF
        // )

        //                 buildah images --json | jq -r "$jq_filter" | sort -r | awk '{print $2}' > all_ids.txt

        //                 head -n 5 all_ids.txt > keep_ids.txt

        //                 echo "🆕 Keeping these image IDs:"
        //                 cat keep_ids.txt

        //                 echo "🗑️ Checking for deletable old image IDs:"
        //                 grep -Fxv -f keep_ids.txt all_ids.txt > delete_ids.txt || true
        //                 cat delete_ids.txt

        //                 if [ ! -s delete_ids.txt ]; then
        //                 echo "✅ No old images to delete."
        //                 fi

        //                 while read -r id; do
        //                     if [ -n "$id" ]; then
        //                         echo "🗑️ Deleting image: $id"
        //                         buildah rmi -f "$id" || echo "⚠️ Could not delete $id"
        //                     fi
        //                 done < delete_ids.txt

        //                 rm -f all_ids.txt keep_ids.txt delete_ids.txt
        //             '''
        //         }
        //     }
        // }

        stage('Clean Up Old Images') {
            steps {
                dir("${env.WORKSPACE}") {
                    sh '''
                        chmod +x ./scripts/cleanup_oldimg.sh
                        ./scripts/cleanup_oldimg.sh
                    '''
                }
            }
        }



        stage('Update YAML and Push to GitHub (Trigger ArgoCD)') {
            steps {
                withCredentials([string(credentialsId: 'github-token', variable: 'GITHUB_TOKEN')]) {
                    script {
                        sh '''
                            echo "🔄 Updating Kubernetes YAML with image: $FULL_IMAGE"

                            sed -i "s|image:.*|image: $FULL_IMAGE|" k8s/api-controller.yaml
                            sed -i "s|image:.*|image: $FULL_IMAGE|" k8s/api-service.yaml

                            for file in k8s/*.yaml; do
                                sed -i "s|^namespace:.*|namespace: $K8S_NAMESPACE|" "$file"
                            done

                            git config --global user.email "jenkins@ci.local"
                            git config --global user.name "Jenkins CI"

                            if ! git diff --quiet k8s/; then
                                git add k8s/
                                git commit -m "Update image to $FULL_IMAGE"
                                git remote set-url origin https://$GITHUB_TOKEN@github.com/bhone121212/fb-worker.git
                                git push origin HEAD:main
                                echo "✅ GitHub pushed with new image tag"
                            else
                                echo "⚠️ No changes in image tag. Skipping GitHub push."
                            fi

                            echo "🚀 Applying Kubernetes resources to $K8S_NAMESPACE"
                            kubectl apply -n $K8S_NAMESPACE -f k8s/worker-controller.yaml
                        '''
                    }
                }
            }
        }
    }

    post {
        success {
            echo '✅ fb-api CI/CD Pipeline executed successfully!'
        }
        failure {
            echo '❌ Pipeline failed. Check logs for issues.'
        }
    }
}