#!/usr/bin/env bash
# Check local prerequisites without reading or printing credential values.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
for tool in docker sbx; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "Missing $tool. See README.md for prerequisites." >&2
    exit 1
  fi
done
docker version --format 'Docker server: {{.Server.Version}}'
sbx version
sbx ls -q >/dev/null

for file in band.yaml main.py pyproject.toml uv.lock fixture/src/slugify.py fixture/tests/test_slugify.py; do
  if [[ ! -f "$ROOT/$file" ]]; then
    echo "Missing $file" >&2
    exit 1
  fi
done
if ! grep -Eq '^[[:space:]]+id:[[:space:]]+[[:xdigit:]-]{36}[[:space:]]*$' "$ROOT/band.yaml" ||
   grep -Eq '^[[:space:]]+id:[[:space:]]+00000000-0000-0000-0000-000000000000' "$ROOT/band.yaml"; then
  echo "Set agent.id in band.yaml to your BAND agent UUID." >&2
  exit 1
fi
if ! grep -Fq 'replace(" ", "-")' "$ROOT/fixture/src/slugify.py"; then
  echo "The fixture may already be repaired. Reset it with: bash scripts/reset-fixture.sh"
fi
echo "Local prerequisites passed (tested with SBX 0.48.0)."
echo "Before creation, store both custom secrets as described in README.md."
echo "Credential validity is checked when the agent connects and calls Claude."
