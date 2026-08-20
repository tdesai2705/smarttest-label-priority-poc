// ─────────────────────────────────────────────────────────────────────────────
// Clean-workspace retest of tag-based test prioritization (see main branch for
// the original POC + findings against the corrupted `tejas` workspace).
//
// This branch targets a brand-new, dedicated Smart Tests workspace (PTS v1)
// created specifically to avoid tejas's known-bad duration data. Running in
// OBSERVATION MODE for now: subset still runs (and the tag-derived mapping is
// still generated/submitted every build, so the mapping data is present from
// build #1), but --observation forces ALL tests to be selected regardless of
// budget, while genuine per-test durations accumulate honestly from build #1
// (no synthetic sleep bolted on later, unlike tejas's history).
//
// Plan: collect 20+ observation runs, review the confidence curve, THEN
// switch to --target / --confidence subset mode and retest the mapping's
// actual effect on selection -- see project-critical-test-prioritization
// memory for full context.
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

        stage('Install Dependencies') {
            steps {
                container('python') {
                    sh '''
                        apt-get update -qq
                        apt-get install -y --no-install-recommends default-jre-headless git >/dev/null
                        pip install --no-cache-dir -r requirements.txt
                        pip install --no-cache-dir "smart-tests-cli~=2.0"
                        smart-tests --version
                    '''
                }
            }
        }

        stage('Smart Tests — Record Build') {
            steps {
                container('python') {
                    withCredentials([string(credentialsId: 'smart-tests-token-ptsv1', variable: 'SMART_TESTS_TOKEN')]) {
                        sh '''
                            git config --global --add safe.directory ${WORKSPACE}
                            smart-tests verify || true
                            smart-tests record build --build ${BUILD_TAG} --source .
                        '''
                    }
                }
            }
        }

        stage('Generate tag-based mapping from pytest markers') {
            steps {
                container('python') {
                    sh '''
                        echo "=== Step 1: collect all tests marked @pytest.mark.critical ==="
                        PYTHONPATH=. pytest tests/ --collect-only -q -m critical | grep "::" > critical-node-ids.txt || true
                        echo "Critical tests found:"
                        cat critical-node-ids.txt

                        echo "=== Step 2: convert pytest node IDs into prioritized-tests-v1 test-case entries ==="
                        python3 - <<'PYEOF'
import json

entries = []
with open("critical-node-ids.txt") as f:
    for line in f:
        node_id = line.strip()
        if not node_id:
            continue
        file_path, testcase = node_id.split("::")
        module = file_path.replace("/", ".").rsplit(".py", 1)[0]
        entries.append(f"file={file_path}#class={module}#testcase={testcase}")

mapping = {
    "format": "prioritized-tests-v1",
    "mappings": {
        ".": {
            "tests": entries
        }
    }
}

with open("smart-tests-mapping.json", "w") as f:
    json.dump(mapping, f, indent=2)

print(json.dumps(mapping, indent=2))
print(f"Generated mapping with {len(entries)} critical test-case entries")
PYEOF
                    '''
                }
            }
        }

        stage('Test — observation mode') {
            steps {
                container('python') {
                    withCredentials([string(credentialsId: 'smart-tests-token-ptsv1', variable: 'SMART_TESTS_TOKEN')]) {
                        sh '''
                            mkdir -p test-results

                            smart-tests record session \\
                                --build ${BUILD_TAG} \\
                                --test-suite label-priority-poc \\
                                --observation \\
                                > session.txt

                            echo "Session: $(cat session.txt)"

                            PYTHONPATH=. pytest tests/ --collect-only -q \\
                                | grep "::" \\
                                | smart-tests --log-level audit subset pytest \\
                                    --session @session.txt \\
                                    --use-case one-commit \\
                                    --prioritized-tests-mapping smart-tests-mapping.json \\
                                    > subset.txt 2> subset_stderr.log

                            echo "=== Smart Tests selected $(wc -l < subset.txt) tests (observation mode = should be ALL) ==="
                            cat subset.txt

                            set --
                            while IFS= read -r line; do
                                set -- "$@" "$line"
                            done < subset.txt

                            PYTHONPATH=. pytest "$@" \\
                                --junitxml=test-results/results.xml \\
                                -v
                        '''
                    }
                }
            }
            post {
                always {
                    container('python') {
                        withCredentials([string(credentialsId: 'smart-tests-token-ptsv1', variable: 'SMART_TESTS_TOKEN')]) {
                            sh '''
                                smart-tests record tests pytest \\
                                    --session @session.txt \\
                                    test-results/results.xml || true
                            '''
                        }
                    }
                    junit 'test-results/results.xml'
                }
            }
        }
    }

    post {
        success {
            echo "Pipeline done | Build: ${BUILD_NUMBER} | Workspace: PTS v1 (81353921-8255-4a5b-a916-aaf9caed3e11)"
        }
    }
}
