#!/usr/bin/env bash
# Run any `bench` command against Podman (via the docker->podman shim + API socket).
# Example: scripts/bench-podman.sh eval run --tasks-dir tasks/arithmetic-trap \
#            --agent oracle --sandbox docker
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/config.sh
export PATH="$(pwd)/scripts/podman:$HOME/.local/bin:$PATH"
export PODMAN_SOCKET DOCKER_HOST="unix://${PODMAN_SOCKET}"
exec bench "$@"
