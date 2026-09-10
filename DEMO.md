# Demo capture guide

Twelve shots, in order, each tied to the command that produces it. Follow README.md
to run the demo; this page tells you when to hit the shutter and why the shot matters.

**Before you start:** widen your terminal to ~100 columns, bump the font, and
`git init && git add -A && git commit` so shot 9 is a real diff. Clear your scrollback
between phases so each screenshot is self-contained.

## Always redact

- Band **Agent UUID** (appears in `band.yaml`, the Band settings page, and possibly logs).
- Any **key value** anywhere. `verify.sh` is written not to print them, but check
  `sbx policy log` output before publishing — redact hostnames you don't want public.
- Your Band **account name / avatar**, if the room screenshots show them.

---

## The shots

| # | After running | Capture | Why it earns its place |
|---|---|---|---|
| 1 | `sbx version` then `./scripts/preflight.sh` | Full terminal, all checks green | Establishes a clean, ordinary Mac and — critically — **records the sbx version**, since the kit documents testing against 0.35.0 |
| 2 | — (Band UI) | The **Connect Remote Agent** form, or the agent's settings page afterwards, UUID redacted | Identity is Band's, not the sandbox's. The subtitle — "brings its own reasoning loop and authenticates via API key" — is the whole thesis in one line |
| 3 | `./scripts/create.sh` | The `sbx create` output — local kit plus published image | **No local build, no repo checkout.** The declarative kit reuses Band's published runtime image |
| 4 | `sbx exec band-repo-doctor tail -n 50 /var/log/sbx-kit-startup.log` | The locked dependency sync, then the agent connecting | The launcher installs `uv.lock` into a sandbox-owned venv and execs your entrypoint. Also shows nothing leaked into the host tree |
| 5 | — (Band UI) | Your `@<user>/repo-doctor` request message | The human ask, in one sentence. The whole interface is a chat message |
| 6 | — (Band UI) | Tool execution events: `list_files`, `read_file`, `run_tests` showing **`1 failed, 3 passed`** and the `hello---world` vs `hello-world` assertion diff | **The money shot.** The agent reproduced the failure before touching anything, and you can read the real pytest output — not a claim about it |
| 7 | — (Band UI) | The `write_source` event, then `run_tests` showing **`4 passed`** | One file written, then verified. The claim and the evidence are separately visible |
| 8 | — (Band UI) | The agent's final summary message | Cause, file changed, result — the deliverable a human actually reads |
| 9 | `git diff -- fixture/src/slugify.py` (or `./scripts/verify.sh` §5) | The one-file diff on the host | The workspace is a real mount. Work done in the VM lands in your working tree — exactly one file |
| 10 | `./scripts/verify.sh` §2 and §3 | `proxy-managed` PASS, and `uid=1000 user=agent` | Two claims at once: **the real keys were never in the VM**, and nothing ran as root |
| 11 | `./scripts/verify.sh` §4 | A redacted excerpt of `sbx policy log` | Egress was Band + PyPI (setup) + the one model provider. Default-deny, not open internet |
| 12 | `sbx stop band-repo-doctor && sbx run --name band-repo-doctor`, then ask a follow-up in the same room | The reconnected agent answering | The agent is durable, not a one-shot script. Bonus criterion |

Plus one asset that isn't a screenshot: **the architecture diagram** from the top of
README.md. Redraw it properly — it carries the argument that there is no inbound
connection to the laptop.

---

## The argument the shots are making

If the post has a thesis, it's the **compositional boundary**:

> Band coordinates the work. Docker Sandbox contains its execution.

Neither product had to know about the other. Band sees an agent that connects over a
WebSocket and posts messages. `sbx` sees a Python process that wants network access to
two hosts. The interesting part is that the seam needed no glue code — the published
kit is the entire integration.

Three details worth a paragraph each, because they're the kind of thing you only learn
by actually running it:

1. **The credential inversion.** The agent authenticates to Band with a key it does not
   have. `BAND_API_KEY` inside the VM is literally the string `proxy-managed`; the
   host-side proxy substitutes the real value on the wire. A prompt injection that
   convinces the agent to print its own credentials gets you the word "proxy-managed".
   Shot 10 is the proof.

2. **Narrow tools are for legibility, not security.** The VM is the security boundary.
   Four scoped tools instead of a shell buy something different: the agent *cannot*
   edit the tests it's being judged by or its own config, so "the tests pass now" is a
   claim with teeth. Worth contrasting with the usual "give the agent bash" demo.

3. **Execution events are opt-in, and the demo is hollow without them.**
   `AdapterFeatures(emit={Emit.EXECUTION})` is off by default. Turn it off and you get
   an agent asserting it fixed the bug; turn it on and you get the pytest output that
   proves it. That's the difference between a demo and a trust story.

If you want a fourth: the boring-but-real integration findings — `band-sdk[langgraph]`
pins `websockets<16`, which cannot connect through the sandbox proxy at all (it answers
`CONNECT` with `HTTP/1.0 200`, which old `websockets` rejects), while the `pydantic-ai`
extra resolves `websockets 17` and just works. And the kit image has no `procps`, so
the obvious `ps` command for proving non-root doesn't exist — you read `/proc` instead.
Sandboxes make dependency and base-image assumptions visible in a way laptops don't.
