// ─────────────────────────────────────────────────────────────────────────────
// Standalone POC: can Smart Tests achieve tag/label-based test prioritization?
//
// Real question (from Usha, Amadeus): Robot Framework lets you tag a test
// "critical" and always run/prioritize those. TTS and Playwright have no
// equivalent native tag mechanism, and Smart Tests' --goal-spec has no
// tag/label-reading function at all (confirmed against the docs).
//
// This tests whether a client-side workaround can deliver the same practical
// outcome: read pytest's own @pytest.mark.critical marker, and dynamically
// generate a --prioritized-tests-mapping file from it every build, so
// "critical" tests are always folded into the subset regardless of what the
// AI-based confidence/target budget alone would have picked.
//
// Deliberately unrelated repo, unrelated Smart Tests test-suite name, no app
// code, no Docker/deploy stages -- purely testing the selection mechanism.
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
                    withCredentials([string(credentialsId: 'SMART_TESTS_TOKEN', variable: 'SMART_TESTS_TOKEN')]) {
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
        # e.g. tests/test_checkout.py::test_payment_processed_successfully
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

        stage('Test') {
            steps {
                container('python') {
                    withCredentials([string(credentialsId: 'SMART_TESTS_TOKEN', variable: 'SMART_TESTS_TOKEN')]) {
                        sh '''
                            mkdir -p test-results

                            smart-tests record session \\
                                --build ${BUILD_TAG} \\
                                --test-suite label-priority-poc \\
                                > session.txt

                            echo "Session: $(cat session.txt)"

                            PYTHONPATH=. pytest tests/ --collect-only -q \\
                                | grep "::" \\
                                | smart-tests --log-level audit subset pytest \\
                                    --session @session.txt \\
                                    --target 50% \\
                                    --use-case one-commit \\
                                    --prioritized-tests-mapping smart-tests-mapping.json \\
                                    > subset.txt 2> subset_stderr.log

                            echo "=== Smart Tests selected $(wc -l < subset.txt) tests ==="
                            cat subset.txt

                            echo "=== DEBUG: full audit log from subset command (stderr) ==="
                            cat subset_stderr.log
                            echo "=== END audit log ==="

                            SUBSET_ID=$(grep -oE 'subset [0-9]+' subset_stderr.log | grep -oE '[0-9]+' | head -1)
                            echo "=== DEBUG: subset id = ${SUBSET_ID} ==="
                            smart-tests inspect subset --subset-id "${SUBSET_ID}" || echo "inspect subset failed"
                            echo "=== END inspect subset ==="

                            echo "=== Verification: are ALL critical tests present in the subset? ==="
                            MISSING=0
                            while IFS= read -r critical_id; do
                                if ! grep -qF "$critical_id" subset.txt; then
                                    echo "MISSING FROM SUBSET: $critical_id"
                                    MISSING=1
                                else
                                    echo "present: $critical_id"
                                fi
                            done < critical-node-ids.txt

                            if [ "$MISSING" = "1" ]; then
                                echo "RESULT: FAIL - at least one critical test was NOT included in the subset"
                            else
                                echo "RESULT: PASS - all critical tests were included in the subset"
                            fi

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
                        withCredentials([string(credentialsId: 'SMART_TESTS_TOKEN', variable: 'SMART_TESTS_TOKEN')]) {
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
            echo "Pipeline done | Build: ${BUILD_NUMBER}"
        }
    }
}
