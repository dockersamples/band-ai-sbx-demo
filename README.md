# Repo Doctor in a Docker Sandbox

Repo Doctor joins a BAND room and repairs a deliberately broken Python project when
you mention it. The agent runs on your machine inside a Docker Sandbox, and its
source edit appears in your local checkout.

In the BAND room, you ask it to diagnose the failing tests, fix only the source,
and report the result. Tool events show the test runs and file edit alongside its
reply. The demo starts with **1 failed, 3 passed** and finishes with **4 passed**,
with only `fixture/src/slugify.py` changed.

This example uses the unchanged published workload
[`bandhq/band-python-kit:6.0.0`](https://hub.docker.com/r/bandhq/band-python-kit).
There is no custom kit, mixin, or image build.

```text
Your browser --> BAND room <-- outbound WebSocket -- Repo Doctor
                                                     |
                                              Docker Sandbox
                                                     |
                                              mounted checkout
```

## How the example runs

The kit reads `band.yaml`, which identifies the BAND agent and tells the launcher
to run `main.py`. That Python file defines a Pydantic AI agent with four tools and
chooses `anthropic:claude-opus-5` as its model.

We chose Claude for this example. That is why this sandbox needs an Anthropic API
key and permission to reach `api.anthropic.com`. The BAND kit supports Python
agents using other models and frameworks; it does not choose Claude for you.

## Run it yourself

### Prerequisites

- A supported [Docker Sandboxes host](https://docs.docker.com/ai/sandboxes/), with
  Docker running and `sbx` installed and signed in (`sbx login`). Tested on macOS
  arm64 with SBX 0.48.0.
- Git and a terminal with Bash for the optional helper scripts.
- A BAND account with a registered remote agent. Save its agent UUID and API key.
- An Anthropic API key with access to the configured model and API credits.
  Claude Code OAuth alone does not authenticate this Pydantic AI example.

Python and `uv` on the host are only needed for development. The published kit
supplies the Python runtime and installs the committed lockfile inside the sandbox.

### 1. Clone and set the BAND identity

```bash
git clone https://github.com/dockersamples/band-ai-sbx-demo.git
cd band-ai-sbx-demo
```

In [BAND](https://app.band.ai/agents), register a remote agent named Repo Doctor,
with a handle such as `repo-doctor`. Save its API key when it is shown. Copy its
agent UUID into `band.yaml`:

```yaml
agent:
  id: YOUR_AGENT_UUID
  entrypoint: main.py
```

Keep the other settings unchanged. The agent runs in your sandbox; no model key
needs to be entered into BAND's hosted-agent settings.

### 2. Store the keys before creating the sandbox

Run these commands on the host, from your checkout. Each prompts for a secret.
Paste the BAND agent key into the first prompt, and the Anthropic API key into
the second. Do not put keys in `band.yaml` or commit them.

```bash
sbx secret set-custom \
  --sandbox band-repo-doctor \
  --host '**.band.ai' \
  --env BAND_API_KEY \
  --placeholder proxy-managed

sbx secret set-custom \
  --sandbox band-repo-doctor \
  --host api.anthropic.com \
  --env ANTHROPIC_PROXY_KEY \
  --placeholder sk-ant-proxy-managed
```

The host proxy holds the real keys and substitutes them into outbound request
headers. Inside the sandbox, the variables contain only the placeholders above.
The example reads `ANTHROPIC_PROXY_KEY` and passes it explicitly to the Anthropic
provider. Both secrets are scoped to `band-repo-doctor`, leaving any global Claude
OAuth configuration unchanged.

Use a new sandbox name if `band-repo-doctor` already belongs to another task.
Substitute that name in every credential, create, policy, and run command below.
Stop any previous runtime using the same BAND agent identity before starting this
one, so two agents do not consume the same room messages.

### 3. Create and start

From the repository root:

```bash
sbx create --name band-repo-doctor \
  docker.io/bandhq/band-python-kit:6.0.0 "$PWD"

sbx policy allow network --sandbox band-repo-doctor api.anthropic.com

sbx run --name band-repo-doctor
```

The kit already permits BAND Cloud and the Python package hosts. The additional
rule permits this example's model endpoint. Existing host or organization policy
also applies; inspect it with `sbx policy ls band-repo-doctor`.

`sbx create` prepares the sandbox. `sbx run` installs the locked workspace
dependencies and launches `main.py`. Keep that terminal open for the agent's
lifetime. The logs should show `Connected to platform` and the agent joining its
BAND rooms. A created sandbox alone does not establish a running agent.

For a terminal session you can detach from, use tmux instead of the last command:

```bash
tmux new-session -s band-repo-doctor 'sbx run --name band-repo-doctor'
```

Detach with Ctrl-b, then d. Reattach with `tmux attach -t band-repo-doctor`.
Use exactly one `sbx run` session for this agent.

Optional: `bash scripts/create.sh` performs the create and policy commands after
local prerequisite checks. It refuses an existing sandbox and prints the run
command. For another name, use `SBX_SANDBOX=my-demo bash scripts/create.sh` after
storing both secrets under that name.

### 4. Ask Repo Doctor to repair the fixture

Add the remote agent to a BAND room and mention its actual handle:

```text
@<your-user>/repo-doctor The project in your workspace has a failing test.
Diagnose it, fix only the source code, run the full test suite,
and report what changed.
```

The expected baseline is **1 failed, 3 passed**: `slugify("hello   world")` produces
`hello---world`. The agent should repair `fixture/src/slugify.py`, rerun the tests,
and report **4 passed**. Tool-call events are enabled so you can inspect the real
test output in the room.

In another host terminal, from this checkout:

```bash
git diff -- fixture/src/slugify.py
bash scripts/verify.sh
```

Verification checks credential placeholders, the running agent's UID, network
logs, and the fixture tests inside the sandbox. It exits nonzero on a failed
check, including an unrepaired fixture. It does not post messages to BAND.
Use `SBX_SANDBOX=my-demo bash scripts/verify.sh` if you chose another name.

## Repeat, restart, or stop

Wait for the current BAND turn to finish, then restore the intentional bug:

```bash
bash scripts/reset-fixture.sh
```

Send another repair request, preferably in a fresh room for a clean demonstration.
The reset affects only the fixture source and its caches. Never reset it while the
agent is working. See [DEMO.md](DEMO.md) for screenshot and evidence guidance.

Stop the sandbox with `sbx stop band-repo-doctor`. Restart it with
`sbx run --name band-repo-doctor` in a terminal. If using tmux, close any old owner
session before starting a new one. Do not assume stop provides graceful teardown.

Removing the sandbox with `sbx rm band-repo-doctor` also removes its scoped
secrets. Before recreating, store both keys again. Keep your keys in your own
secure credential store; SBX is not a way to recover a one-time BAND key.

## How the example is bounded

The four tools list files under `fixture/`, read fixture files, write existing
files under `fixture/src/`, and execute the fixed pytest command. The writing tool
cannot edit the test files or agent configuration. Paths that resolve outside the
permitted root are rejected. The agent has no general shell tool.

The microVM is the isolation boundary. The narrower tool set makes this demo
predictable; it is not a general-purpose filesystem security mechanism. The host
checkout is deliberately writable and receives the agent's changes.

## Develop and test

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then run:

```bash
uv sync --locked
uv run --locked pytest
uv run --locked ruff check .
uv run --locked ruff format --check .
```

The root test suite validates the tool boundaries, the SDK adapter setup, and the
fixture's failure-to-success transition in a temporary copy. It needs no API key,
BAND account, or sandbox. The separate `fixture/tests/` suite is intentionally
failing in a fresh checkout; do not fix its source to make CI green.

Update both `pyproject.toml` and `uv.lock` for dependency changes (`uv lock`), then
restart the sandbox to sync them. To select another Anthropic model supported by
your account, restart the agent with:

```bash
sbx run --name band-repo-doctor \
  --env REPO_DOCTOR_MODEL=anthropic:YOUR_MODEL_ID
```

Using a different provider also requires changing the Python provider wiring,
credentials, and network rule. The example's model override selects Anthropic
models only.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| `ANTHROPIC_PROXY_KEY` missing | Store the custom secret before creation. A sandbox created earlier may lack its environment variable; preserve your keys before recreating. |
| BAND authentication fails | Confirm the UUID matches the BAND key and the custom secret targets the configured BAND host. |
| Claude returns 401, 403, or a billing/model error | Check your Anthropic API key, API credits, and access to the configured model. Claude Code OAuth is a separate setup. |
| Network request blocked | Inspect `sbx policy log band-repo-doctor`; allow the required hostname. Organization policy may require administrator action. |
| Sandbox exists but agent is offline | Keep `sbx run --name band-repo-doctor` active in a terminal or tmux. |
| Locked dependency sync fails | Run `uv lock` after dependency edits, commit the lockfile, and restart. |
| No repair needed | Wait for the agent to finish, then run `bash scripts/reset-fixture.sh`. |

Do not override sandbox-managed proxy variables. Launcher diagnostics are in the
run terminal and `/home/agent/.local/share/band-kit/logs/launcher.log`. The old
`/var/log/sbx-kit-startup.log` path does not contain this v3 agent's runtime output.

## Validated configuration

| Component | Tested value |
| --- | --- |
| Host | macOS arm64 |
| SBX | 0.48.0 |
| Published BAND workload | `docker.io/bandhq/band-python-kit:6.0.0` (kit schema v3) |
| Workload digest | `sha256:5976165107628bc7ad9512bfec5c6e72c1a60e29511132453698a54114f279a8` |
| BAND SDK | 6.0.0 |
| Model | `anthropic:claude-opus-5` |

On October 20, 2026, this configuration authenticated through the host proxy,
received a BAND-room request, edited only the fixture source, emitted tool events,
posted its reply, and completed the turn. An independent test run confirmed four
passing tests. The implementation was tested with the stock published workload.

## License

[Apache License 2.0](LICENSE).
