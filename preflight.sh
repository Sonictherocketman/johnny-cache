#! /bin/bash

# A simple preflight script that runs the same checks that CircleCI runs.
set -e;

log() {
    echo "[$(date)] $1";
}

cat << EOF
----------------------------------
Running preflight checks...
----------------------------------
EOF

log "Linting...";
flake8

log "Running the tests...";
pytest

cat << EOF
----------------------------------
Done! Ready to ship. 🚀
----------------------------------
EOF
