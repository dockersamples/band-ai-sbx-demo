# Capture the Repo Doctor demo

Follow [README.md](README.md) to configure the remote agent and start the published
BAND workload. Keep the `sbx run` terminal open while capturing the BAND room.

## Capture sequence

1. Show the BAND remote agent registration or agent details. Hide the API key and
   redact personal account details and the agent UUID before publishing.
2. Capture `sbx create` using `docker.io/bandhq/band-python-kit:6.0.0`, the Anthropic
   network grant, and `sbx run`. No local kit or image build is involved.
3. Show the terminal's `Connected to platform` message. Launch output includes
   identifiers, so inspect it before sharing.
4. In a room with Repo Doctor added, mention its handle with the README's repair
   request. Capture the request and the test/tool events, including the initial
   failure and the final four passing tests.
5. Capture the agent's reply and `git diff -- fixture/src/slugify.py` on the host.
   The test files must remain unchanged.

Run `bash scripts/verify.sh` from the mounted checkout after the turn completes.
It checks the runtime and reruns the tests. Network policy logs show requests, not
proof that a model reply or a repair completed; verify the reply and file diff too.

The existing PNGs in this repository are from the earlier demo and show older UI
and setup commands. They are historical references, not screenshots of kit 6.0.0.
Replace them with newly reviewed captures for publication. Do not publish keys,
unredacted identifiers, or private conversation history.

## Repeat the demo

Wait until the turn completes, then run `bash scripts/reset-fixture.sh`. Start a
fresh BAND room for a clean screenshot sequence and add the same remote agent.
Do not run two sandbox agents with the same BAND identity simultaneously.

The main story is the room request causing work inside the sandbox and the result
returning to BAND. Pydantic AI and Claude are choices made in this example's
`main.py`; `band.yaml` tells the stock kit which entrypoint to launch.
