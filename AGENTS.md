# Workspace context

This workspace is a Band remote agent ("Repo Doctor") launched by the
`band-python-kit` Docker Sandbox kit.

- `main.py` is the entrypoint the kit launcher execs. Agent identity and endpoints
  arrive as `BAND_*` environment variables.
- `band.yaml` holds agent configuration. It is strictly validated — unknown fields
  fail the launch.
- `fixture/` is a **deliberately broken** sample project. It is the demo's subject
  matter, not a bug to fix in passing. `scripts/reset-fixture.sh` restores its
  known-broken state.
- Dependency changes must update both `pyproject.toml` and `uv.lock` (`uv lock`),
  and take effect on the next sandbox restart.
- Network access is default-deny. Add only the exact host a task needs, scoped to
  this sandbox: `sbx policy allow network --sandbox band-repo-doctor <host>`.
- Never print or commit configured credentials. The real keys are not in this VM —
  `BAND_API_KEY` and `ANTHROPIC_API_KEY` read as sentinel placeholders by design.
