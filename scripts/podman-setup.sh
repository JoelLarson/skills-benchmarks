#!/usr/bin/env bash
# Preflight for running the benchmark on Podman instead of Docker.
# Verifies podman, the Docker-API socket, Compose v2, and the docker->podman shim.
set -uo pipefail
cd "$(dirname "$0")/.."
source scripts/config.sh

sock="${PODMAN_SOCKET:-${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/podman/podman.sock}"
fail=0

echo "1) podman binary"
if command -v podman >/dev/null 2>&1; then echo "   ok: $(podman --version)"; else
  echo "   MISSING — install podman"; fail=1; fi

echo "2) podman API socket (Docker-compatible)"
if [[ -S "$sock" ]]; then echo "   ok: $sock"; else
  echo "   not active — attempting: systemctl --user enable --now podman.socket"
  systemctl --user enable --now podman.socket 2>/dev/null || true
  if [[ -S "$sock" ]]; then echo "   ok: $sock"; else
    echo "   FAILED to activate. Try manually: systemctl --user enable --now podman.socket"; fail=1; fi
fi

echo "3) Compose v2 binary (recommended; podman-compose is unreliable for 'up --wait')"
if command -v docker-compose >/dev/null 2>&1 || [[ -x "$HOME/.docker/cli-plugins/docker-compose" ]]; then
  echo "   ok: Compose v2 found"
else
  echo "   NOT found. Install without sudo:"
  echo "     mkdir -p ~/.local/bin"
  echo "     curl -fsSL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 \\"
  echo "       -o ~/.local/bin/docker-compose && chmod +x ~/.local/bin/docker-compose"
  echo "   (ensure ~/.local/bin is on PATH). The shim falls back to 'podman compose' otherwise."
fi

echo "4) docker->podman shim self-test (bare 'docker info', as bench invokes it)"
if PATH="$(pwd)/scripts/podman:$PATH" PODMAN_SOCKET="$sock" \
     docker info >/dev/null 2>/tmp/_podman_shim_err; then
  echo "   ok: 'docker info' served by podman"
else
  echo "   FAILED: $(cat /tmp/_podman_shim_err)"; fail=1
fi
rm -f /tmp/_podman_shim_err

echo
if [[ "$fail" == "0" ]]; then
  echo "Podman preflight passed. run_pilot.sh (USE_PODMAN=1) will use Podman via --sandbox docker."
else
  echo "Podman preflight had failures above — resolve them before running the pilot."
  exit 1
fi
