#!/usr/bin/env bash
# Create the demo sandbox from the repo-local, Claude-specific Band kit. The kit
# declares both the Anthropic host allowlist and proxy-managed credential binding,
# so the agent is ready on its first start.
#
# Kit changes apply only at creation time, so to pick up an edit to band.yaml's
# credential tier or a different kit tag you must `sbx rm` and re-create.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SANDBOX="${SBX_SANDBOX:-band-repo-doctor}"
KIT="${BAND_KIT:-$ROOT/band-kit-fix}"

"$ROOT/scripts/preflight.sh"

if sbx inspect "$SANDBOX" >/dev/null 2>&1; then
  echo
  echo "error: sandbox '$SANDBOX' already exists." >&2
  echo "       Kit configuration is applied only at creation, so reuse is not safe here." >&2
  echo "       Remove it first:  sbx rm $SANDBOX" >&2
  exit 1
fi

echo
echo "==> Creating sandbox '$SANDBOX' from $KIT"
echo "    workspace: $ROOT"
# The published image is pulled by the sandbox runtime; the local kit is only a
# declarative wrapper. The agent launches headlessly as soon as creation finishes.
sbx create --name "$SANDBOX" --kit "$KIT" band-python-kit "$ROOT"

cat <<EOF

Sandbox '$SANDBOX' is up and the agent is connecting to Band.

Watch it come up:
  sbx exec $SANDBOX tail -n 50 -f /var/log/sbx-kit-startup.log

Then, in a Band room with your agent added, send:
  @<your-agent> The project in your workspace has a failing test. Diagnose it,
  fix only the source code, run the full test suite, and report what changed.

Afterwards, collect the evidence:
  scripts/verify.sh
EOF
