#!/usr/bin/env bash
# Create from BAND's published workload, then grant the example's model endpoint.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SANDBOX="${SBX_SANDBOX:-band-repo-doctor}"
KIT="docker.io/bandhq/band-python-kit:6.0.0"

bash "$ROOT/scripts/preflight.sh"
names="$(sbx ls -q)"
if grep -Fxq -- "$SANDBOX" <<<"$names"; then
  echo "Sandbox '$SANDBOX' already exists. Use sbx run --name '$SANDBOX' to restart it." >&2
  echo "Choose a different SBX_SANDBOX name for a fresh run." >&2
  exit 1
fi

sbx create --name "$SANDBOX" "$KIT" "$ROOT"
sbx policy allow network --sandbox "$SANDBOX" api.anthropic.com
printf '\nCreated %s. Start the agent and keep its terminal open:\n' "$SANDBOX"
printf '  sbx run --name %q\n' "$SANDBOX"
