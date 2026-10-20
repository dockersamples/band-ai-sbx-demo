"""Repo Doctor — a Band agent that repairs a broken Python project from inside a Docker Sandbox.

The band-python-kit launcher execs this file with the workspace's own locked venv
interpreter. Band identity, endpoints, and credentials arrive as BAND_* environment
variables; the real keys never enter the VM (the sandbox proxy holds them and the
process only sees nonsecret placeholders).

The agent is deliberately given four narrow tools instead of a shell. The sandbox is
the real isolation boundary, but a small tool surface keeps the demo predictable and
makes it impossible for the model to edit its own configuration or the tests it is
being judged by.
"""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import sys
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from band import Agent
from band.adapters.pydantic_ai import PydanticAIAdapter, PydanticAIAdapterConfig
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.providers.anthropic import AnthropicProvider
from band.core.types import Emit
from band.runtime.shutdown import run_with_graceful_shutdown

# ── Sandboxed roots ───────────────────────────────────────────────────────────
# Resolved once, at import, so every later comparison is against a real path and
# not something a tool argument could still redirect.
WORKSPACE = Path(__file__).resolve().parent
FIXTURE_ROOT = (WORKSPACE / "fixture").resolve()
SOURCE_ROOT = (FIXTURE_ROOT / "src").resolve()

# Tool output cap. Test output and file contents are bounded so a runaway failure
# can't blow out the model's context or the Band room.
MAX_OUTPUT_CHARS = 20_000

# Directory names that are never interesting to the agent and only add noise.
SKIPPED_DIRS = frozenset(
    {".git", "__pycache__", ".pytest_cache", ".venv", "venv", ".ruff_cache", ".mypy_cache"}
)

MODEL = os.environ.get("REPO_DOCTOR_MODEL", "anthropic:claude-opus-5")

SYSTEM_PROMPT = """\
You are Repo Doctor. You work only inside the provided fixture project, and only \
through your tools — you have no shell and no access to anything else on the machine.

When asked to repair the project: inspect the files, reproduce the failure by running \
the tests, make the smallest source-only fix, then rerun the full test suite to confirm \
it passes. Never modify tests — they define the required behaviour. Preserve the \
behaviour the passing tests already cover.

Reply in the Band room with the cause of the failure, the file you changed, and the \
final test result. If a tool fails, report the failure instead of claiming success. \
Never claim a test passed unless run_tests actually reported it.\
"""


# ── Path safety ───────────────────────────────────────────────────────────────
def _resolve_within(root: Path, candidate: str) -> Path:
    """Resolve ``candidate`` under ``root``, refusing anything that escapes it.

    Rejects absolute paths, ``..`` traversal, and symlinks that point outside the
    root. ``Path.resolve()`` collapses ``..`` and follows symlinks, so comparing the
    resolved result against the resolved root catches both in one check.
    """
    if not candidate or not candidate.strip():
        raise ValueError("path must not be empty")

    supplied = Path(candidate)
    if supplied.is_absolute():
        raise ValueError(f"absolute paths are not allowed: {candidate!r}")

    unresolved = root / supplied
    # A symlink at the leaf could still resolve inside the root; refuse writing
    # through one regardless, so the target on disk is always the literal path.
    if unresolved.is_symlink():
        raise ValueError(f"symlinks are not allowed: {candidate!r}")

    target = unresolved.resolve()
    if target != root and root not in target.parents:
        raise ValueError(f"path escapes {root.name}/: {candidate!r}")
    return target


def _bounded(text: str) -> str:
    if len(text) <= MAX_OUTPUT_CHARS:
        return text
    dropped = len(text) - MAX_OUTPUT_CHARS
    return f"{text[:MAX_OUTPUT_CHARS]}\n… [truncated, {dropped} more characters]"


# ── Tools ─────────────────────────────────────────────────────────────────────
# These are plain, context-free callables. PydanticAIAdapter registers them with
# pydantic-ai's agent.tool_plain(), deriving each schema and description from the
# signature and docstring below — so the docstrings are the tool contract.
def list_files() -> str:
    """List every file in the fixture project.

    Paths are relative to the fixture root. Caches and version-control directories
    are omitted. Use this first to see what the project contains.
    """
    paths: list[str] = []
    for path in sorted(FIXTURE_ROOT.rglob("*")):
        if any(part in SKIPPED_DIRS for part in path.parts):
            continue
        if not path.is_file() or path.suffix == ".pyc":
            continue
        paths.append(str(path.relative_to(FIXTURE_ROOT)))
    if not paths:
        return "The fixture project is empty."
    return "\n".join(paths)


def read_file(path: str) -> str:
    """Read a UTF-8 text file from the fixture project.

    Args:
        path: File path relative to the fixture root, for example
            ``src/slugify.py`` or ``tests/test_slugify.py``.
    """
    try:
        target = _resolve_within(FIXTURE_ROOT, path)
    except ValueError as exc:
        return f"ERROR: {exc}"
    if not target.is_file():
        return f"ERROR: no such file: {path!r}"
    try:
        return _bounded(target.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        return f"ERROR: {path!r} is not valid UTF-8 text"
    except OSError as exc:
        return f"ERROR: could not read {path!r}: {exc}"


def write_source(path: str, content: str) -> str:
    """Overwrite a source file under the fixture's ``src/`` directory.

    Only source files can be written. Tests are read-only: they define the required
    behaviour and must not be changed. The file must already exist.

    Args:
        path: File path relative to the fixture's ``src/`` directory, for example
            ``slugify.py``.
        content: The complete new contents of the file.
    """
    try:
        target = _resolve_within(SOURCE_ROOT, path)
    except ValueError as exc:
        return f"ERROR: {exc}"
    if not target.is_file():
        return f"ERROR: no such source file: {path!r} (write_source cannot create new files)"
    try:
        target.write_text(content, encoding="utf-8")
    except OSError as exc:
        return f"ERROR: could not write {path!r}: {exc}"
    line_count = content.count("\n") + 1
    return f"Wrote {line_count} lines to src/{target.relative_to(SOURCE_ROOT)}."


def run_tests() -> str:
    """Run the fixture project's full pytest suite and return the result.

    Returns the process exit code and the captured output. Exit code 0 means every
    test passed. This is the only source of truth about whether the project works.
    """
    try:
        proc = subprocess.run(
            # -p no:cacheprovider: the workspace is a host mount, so keep pytest
            # from leaving a .pytest_cache directory in the user's working tree —
            # the only file that should change on the host is the one the agent fixes.
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests"],
            cwd=FIXTURE_ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        return "ERROR: the test suite did not finish within 120 seconds."
    except OSError as exc:
        return f"ERROR: could not run pytest: {exc}"

    output = (proc.stdout + proc.stderr).strip() or "(no output)"
    verdict = "all tests passed" if proc.returncode == 0 else "tests failed"
    return f"exit code {proc.returncode} ({verdict})\n\n{_bounded(output)}"


# ── Band wiring ───────────────────────────────────────────────────────────────
class RepoDoctorSettings(BaseSettings):
    """Band identity and endpoints, injected by the kit launcher as BAND_* env vars.

    A missing variable fails loud at startup with a clear validation error rather
    than surfacing later as an opaque connection failure.
    """

    model_config = SettingsConfigDict(env_prefix="BAND_", case_sensitive=False)

    agent_id: str  # BAND_AGENT_ID
    api_key: str  # BAND_API_KEY
    ws_url: str  # BAND_WS_URL
    rest_url: str  # BAND_REST_URL


async def main() -> None:
    settings = RepoDoctorSettings()

    provider_key = os.environ.get("ANTHROPIC_PROXY_KEY")
    if not provider_key:
        raise RuntimeError(
            "ANTHROPIC_PROXY_KEY is missing. Store the sandbox-scoped custom "
            "secret before creating the sandbox; see README.md."
        )
    if not MODEL.startswith("anthropic:"):
        raise ValueError("This example expects REPO_DOCTOR_MODEL=anthropic:<model-id>")

    adapter = PydanticAIAdapter(
        PydanticAIAdapterConfig(custom_section=SYSTEM_PROMPT),
        llm=AnthropicModel(
            MODEL.removeprefix("anthropic:"),
            provider=AnthropicProvider(api_key=provider_key),
        ),
        additional_tools=[list_files, read_file, write_source, run_tests],
        # Publish tool calls and results alongside the agent's explanation.
        emit={Emit.TOOL_CALLS},
    )

    agent = Agent.create(
        adapter=adapter,
        agent_id=settings.agent_id,
        api_key=settings.api_key,
        ws_url=settings.ws_url,
        rest_url=settings.rest_url,
    )
    # Handle delivered signals; sandbox stop does not guarantee graceful teardown.
    await run_with_graceful_shutdown(agent)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
