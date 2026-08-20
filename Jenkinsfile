// ─────────────────────────────────────────────────────────────────────────────
// OIDC handshake test only. Per Anudeep's guidance: don't generate a
// SMART_TESTS_TOKEN api key, use Jenkins OIDC id-token auth instead
// (https://docs.cloudbees.com/docs/cloudbees-smart-tests/latest/send-data-to-smart-tests/set-up-smart-tests/oidc-pipeline-authentication).
//
// First run is EXPECTED to report the subject as unregistered and print a
// JSON block (issuer + normalized-sub) that must be pasted into this
// workspace's Settings -> Trusted OIDC subjects. Subsequent runs then
// authenticate automatically. This branch's job URL is the "sub" -- kept on
// its own branch (distinct job URL) so it can be registered against exactly
// one Smart Tests workspace.
// ─────────────────────────────────────────────────────────────────────────────

pipeline {
    agent {
        kubernetes {
            yaml """
apiVersion: v1
kind: Pod
spec:
  serviceAccountName: jenkins-agents
  containers:
  - name: jnlp
    resources:
      requests:
        cpu: "10m"
        memory: "256Mi"
      limits:
        cpu: "500m"
        memory: "512Mi"
  - name: python
    image: python:3.13-slim
    command: [sleep]
    args: [99d]
    resources:
      requests:
        cpu: "10m"
        memory: "256Mi"
      limits:
        cpu: "1"
        memory: "1Gi"
"""
        }
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Install Smart Tests CLI') {
            steps {
                container('python') {
                    sh '''
                        apt-get update -qq
                        apt-get install -y --no-install-recommends default-jre-headless git >/dev/null
                        pip install --no-cache-dir "smart-tests-cli~=2.0"
                        smart-tests --version
                    '''
                }
            }
        }

        stage('OIDC verify') {
            steps {
                container('python') {
                    withCredentials([string(credentialsId: 'smart-tests-oidc-token', variable: 'SMART_TESTS_OIDC_TOKEN')]) {
                        sh '''
                            git config --global --add safe.directory ${WORKSPACE}
                            export SMART_TESTS_BASE_URL=https://api.cloudbees.io
                            echo "=== JOB_URL (expected sub) ==="
                            echo "${JOB_URL}"
                            echo "=== smart-tests verify --oidc ==="
                            smart-tests verify --oidc || true
                        '''
                    }
                }
            }
        }
    }
}
