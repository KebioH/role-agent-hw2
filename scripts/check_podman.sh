#!/bin/sh
set -eu
# Run from repository root. This script only builds/tests isolated classroom tools.
mkdir -p evidence
podman --version > evidence/podman-version.txt
podman build -f Containerfile -t role-agent-hw2:local .
podman run --rm role-agent-hw2:local > evidence/podman-tests.txt 2>&1
podman run --rm role-agent-hw2:local python scripts/demo.py > evidence/podman-demo.json
cat evidence/podman-tests.txt
