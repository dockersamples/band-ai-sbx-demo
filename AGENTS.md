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
- Never print or commit configured credentials or personal agent IDs.
  `BAND_API_KEY` and `ANTHROPIC_PROXY_KEY` contain nonsecret proxy placeholders.
- Use the unchanged published workload `docker.io/bandhq/band-python-kit:6.0.0`.
  There is no local kit or image build. Create first, then run in a persistent terminal.
- Run `uv run --locked pytest` for the agent's regression tests. The separate
  fixture suite must initially fail (1 failed, 3 passed); never "fix" it for CI.
