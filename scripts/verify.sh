#!/usr/bin/env bash
# Collect the demo's evidence: the agent started, the real keys are not in the VM,
# nothing runs as root, egress stayed narrow, and the fix landed on the host.
#
# Safe to run repeatedly. Prints no secret values — the point of section 2 is that
# the value inside the VM is a sentinel.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SANDBOX="${SBX_SANDBOX:-band-repo-doctor}"
OUTPUT_FILE="${VERIFY_OUTPUT:-$ROOT/repo-doctor-verification.log}"

# Preserve the complete terminal report for the blogpost while still showing it
# live. Override the destination with VERIFY_OUTPUT=/path/to/report.log.
exec > >(tee "$OUTPUT_FILE") 2>&1
echo "Writing complete verification report to: $OUTPUT_FILE"

section() { printf '\n── %s %s\n\n' "$*" "$(printf '─%.0s' {1..30})"; }

section "1. Startup log (last 30 lines)"
sbx exec "$SANDBOX" tail -n 30 /var/log/sbx-kit-startup.log \
  || echo "could not read the startup log — is the sandbox running? (sbx run --name $SANDBOX)"

section "2. The VM holds placeholders, not the real API keys"
if sbx exec "$SANDBOX" sh -lc \
    'test "$BAND_API_KEY" = proxy-managed && test "$ANTHROPIC_API_KEY" = proxy-managed'; then
  echo 'PASS: BAND_API_KEY and ANTHROPIC_API_KEY are exactly "proxy-managed".'
  echo '      The real keys never leave the host; the proxy injects them on the wire.'
else
  echo 'FAIL: one or both API key variables are not the expected sentinel.'
  echo '      Check the host-side secrets, band.yaml credential tier, and the kit'
  echo '      credential declaration before recreating the sandbox.'
fi

section "3. The long-running agent runs as non-root"
# The kit image is python:slim and does NOT ship procps, so there is no `ps`.
# Read the process table straight out of /proc instead. Note that a fresh
# `sbx exec` is itself root regardless of what PID 1 dropped to — which is
# exactly why this inspects the main.py process rather than running `whoami`.
sbx exec "$SANDBOX" sh -lc '
  found=0
  for d in /proc/[0-9]*; do
    [ -r "$d/comm" ] && [ "$(cat "$d/comm")" = python ] || continue
    [ -r "$d/cmdline" ] || continue
    cmd=$(tr "\0" " " < "$d/cmdline" 2>/dev/null) || continue
    case "$cmd" in
      *main.py*)
        uid=$(grep -E "^Uid:" "$d/status" | tr -s " \t" " " | cut -d" " -f2)
        user=$(grep -E "^[^:]*:x:$uid:" /etc/passwd | cut -d: -f1)
        printf "pid=%s uid=%s user=%s\n  cmd=%s\n" "${d#/proc/}" "$uid" "${user:-?}" "$cmd"
        found=1
        ;;
    esac
  done
  [ "$found" = 1 ] || echo "no main.py process found — the agent may not be running"
' || echo "could not inspect the process table"

section "4. Network policy: what was allowed and what was blocked"
sbx policy log "$SANDBOX" || echo "could not read the policy log"

section "5. The agent's edit is visible on the host"
echo "fixture/src/slugify.py as it now stands on this machine:"
echo
sed 's/^/    /' "$ROOT/fixture/src/slugify.py"
echo
if git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "git diff:"
  git -C "$ROOT" --no-pager diff -- fixture/src/slugify.py || true
else
  echo "(not a git repository — run 'git init && git add -A && git commit' before the"
  echo " demo if you want a real 'git diff' for the writeup)"
fi

section "6. Do the tests actually pass now, checked from the host?"
if command -v uv >/dev/null 2>&1; then
  ( cd "$ROOT/fixture" && uv --no-config run --with pytest --no-project \
      python -m pytest -q -p no:cacheprovider tests ) \
    || echo "(non-zero exit — the suite is not green)"
else
  echo "uv not found; run the suite yourself with a Python that has pytest:"
  echo "  (cd \"$ROOT/fixture\" && python3 -m pytest -q)"
fi
