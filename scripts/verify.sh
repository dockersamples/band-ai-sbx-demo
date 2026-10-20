#!/usr/bin/env bash
# Verify runtime identity, credential placeholders and the repaired fixture.
# Returns nonzero if a check fails; run after the BAND repair turn completes.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SANDBOX="${SBX_SANDBOX:-band-repo-doctor}"
PYTHON="/home/agent/.local/share/band-kit/venv/bin/python"
FAILED=0

if ! sbx exec "$SANDBOX" /opt/band/venv/bin/python -c '
import os
from pathlib import Path
assert os.environ.get("BAND_API_KEY") == "proxy-managed", "BAND placeholder missing"
assert os.environ.get("ANTHROPIC_PROXY_KEY") == "sk-ant-proxy-managed", "Anthropic placeholder missing"
processes = []
for path in Path("/proc").glob("[0-9]*/cmdline"):
    try:
        args = path.read_bytes().split(b"\0")
        if not any(arg.endswith(b"/main.py") or arg == b"main.py" for arg in args):
            continue
        uid = next(line.split()[1:] for line in path.with_name("status").read_text().splitlines()
                   if line.startswith("Uid:"))
    except FileNotFoundError:
        continue
    assert all(value == "1000" for value in uid), "Agent is not running as UID 1000"
    processes.append(path.parent.name)
assert processes, "No running main.py process; start sbx run in another terminal"
print("PASS: both credential placeholders present; agent running as UID 1000")
'; then
  FAILED=1
fi

sbx policy log "$SANDBOX" || FAILED=1
git -C "$ROOT" --no-pager diff -- fixture/src/slugify.py || FAILED=1
sbx exec -w "$ROOT/fixture" "$SANDBOX" "$PYTHON" \
  -m pytest -q -p no:cacheprovider tests || FAILED=1
exit "$FAILED"
