#!/usr/bin/env bash
# Check that this host and workspace are ready to create the demo sandbox.
# Reports names and readiness only — never secret values.
#
# sbx flags used here come from the band-python-kit README and Docker's sbx docs.
# If a flag is rejected, check `sbx <command> --help`: the CLI surface changes
# between releases.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SANDBOX="${SBX_SANDBOX:-band-repo-doctor}"
FAILED=0

ok()   { printf '  \033[32m✓\033[0m %s\n' "$*"; }
warn() { printf '  \033[33m!\033[0m %s\n' "$*"; }
bad()  { printf '  \033[31m✗\033[0m %s\n' "$*"; FAILED=1; }
section() { printf '\n\033[1m%s\033[0m\n' "$*"; }

section "Tooling"
if command -v docker >/dev/null 2>&1; then
  if docker version --format '{{.Server.Version}}' >/dev/null 2>&1; then
    ok "docker $(docker version --format '{{.Server.Version}}' 2>/dev/null) (daemon reachable)"
  else
    bad "docker is installed but the daemon is not reachable — start Docker Desktop"
  fi
else
  bad "docker not found — install Docker Desktop"
fi

if command -v sbx >/dev/null 2>&1; then
  ok "sbx $(sbx version 2>/dev/null | head -n1 || echo '(version unknown)')"
  warn "the kit documents testing against sbx 0.35.0 — record the version above for the writeup"
else
  bad "sbx not found — install with: brew trust docker/tap && brew install docker/tap/sbx"
fi

section "Docker sign-in"
if command -v sbx >/dev/null 2>&1; then
  if sbx ls >/dev/null 2>&1; then
    ok "sbx can talk to the sandbox runtime"
    if sbx inspect "$SANDBOX" >/dev/null 2>&1; then
      warn "sandbox '$SANDBOX' already exists — kit changes only apply at creation."
      warn "to recreate it: sbx rm $SANDBOX"
    else
      ok "sandbox '$SANDBOX' does not exist yet"
    fi
  else
    bad "'sbx ls' failed — run: sbx login"
  fi
fi

section "Host virtualization"
case "$(uname -s)" in
  Darwin)
    ok "macOS — sbx uses Apple's native virtualization, nothing to configure"
    ;;
  Linux)
    if [[ -e /dev/kvm ]]; then
      if [[ -r /dev/kvm && -w /dev/kvm ]]; then
        ok "/dev/kvm present and accessible"
      else
        bad "/dev/kvm exists but is not accessible — run: sudo usermod -aG kvm \$USER && newgrp kvm"
      fi
    else
      bad "/dev/kvm missing — this host cannot run sandboxes (nested virtualization required)"
    fi
    ;;
  *)
    warn "unrecognised platform $(uname -s) — verify sbx support manually"
    ;;
esac

section "Workspace"
for f in band.yaml main.py pyproject.toml uv.lock fixture/src/slugify.py fixture/tests/test_slugify.py; do
  if [[ -f "$ROOT/$f" ]]; then ok "$f"; else bad "missing: $f"; fi
done

if grep -Eq '^\s*id:\s*(replace-with-agent-id|00000000-0000-0000-0000-000000000000)\s*$' "$ROOT/band.yaml" 2>/dev/null; then
  bad "band.yaml still has the placeholder agent id — paste your Agent UUID from app.band.ai/agents"
else
  ok "band.yaml agent.id has been set"
fi

if grep -q 'replace(" ", "-")' "$ROOT/fixture/src/slugify.py" 2>/dev/null; then
  ok "fixture is in its known-broken state"
else
  warn "fixture does not look broken — a previous run may have fixed it."
  warn "restore it with: scripts/reset-fixture.sh"
fi

section "Host-held credentials (names only, never values)"
if command -v sbx >/dev/null 2>&1; then
  secrets="$(sbx secret ls 2>/dev/null || true)"
  if [[ -z "$secrets" ]]; then
    warn "could not list secrets ('sbx secret ls' produced no output) — verify manually"
  else
    if grep -qi 'anthropic' <<<"$secrets"; then
      ok "an Anthropic provider secret is configured"
    else
      bad "no Anthropic secret found — run: sbx secret set -g anthropic"
    fi
    if grep -qi 'band\.ai' <<<"$secrets"; then
      ok "a band.ai custom secret is configured"
    else
      bad "no band.ai secret found — see README 'Store the Band API key'"
    fi
  fi
fi

printf '\n'
if (( FAILED )); then
  printf '\033[31mPreflight failed.\033[0m Fix the ✗ items above, then re-run.\n'
  exit 1
fi
printf '\033[32mPreflight passed.\033[0m Next: scripts/create.sh\n'
