#!/usr/bin/env bash
# Restore the fixture's deliberately broken source, so the demo can be run again
# from a known state.
#
# This script is the single source of truth for the broken implementation: the
# heredoc below is exactly what fixture/src/slugify.py should contain before a run.
# It touches nothing else — not credentials, not band.yaml, not the tests.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="$ROOT/fixture/src/slugify.py"

# Anchor on the tests rather than on src/, so this also works on a fresh clone
# where src/ has yet to be written — while still refusing to run in a stray directory.
if [[ ! -f "$ROOT/fixture/tests/test_slugify.py" ]]; then
  echo "error: $ROOT/fixture/tests/test_slugify.py not found — is this the right workspace?" >&2
  exit 1
fi
mkdir -p "$ROOT/fixture/src"

cat > "$TARGET" <<'PYTHON'
"""Turn arbitrary text into a URL slug.

Deliberately broken for the Repo Doctor demo: run scripts/reset-fixture.sh to
restore this exact content between runs.
"""


def slugify(text: str) -> str:
    return text.strip().lower().replace(" ", "-")
PYTHON

# Drop caches so a rerun cannot be confused by a stale bytecode or pytest cache.
rm -rf "$ROOT/fixture/.pytest_cache" "$ROOT/fixture/src/__pycache__" \
       "$ROOT/fixture/tests/__pycache__"

echo "Restored the broken fixture: fixture/src/slugify.py"
echo
echo "Verify the intended failure with the host's own Python:"
echo "  (cd \"$ROOT/fixture\" && python3 -m pytest -q)"
echo "Expected: 1 failed, 3 passed — the failure is repeated-whitespace handling."
