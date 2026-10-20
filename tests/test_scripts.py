"""Exercise command order and failure propagation with a fake SBX executable."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def host(tmp_path):
    repo = tmp_path / "repo"
    shutil.copytree(
        Path(__file__).resolve().parents[1],
        repo,
        ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", ".pytest_cache", "*.png"),
    )
    config = repo / "band.yaml"
    config.write_text(
        config.read_text().replace(
            "00000000-0000-0000-0000-000000000000", "00000000-0000-0000-0000-000000000001"
        )
    )
    binaries = tmp_path / "bin"
    binaries.mkdir()
    sbx = binaries / "sbx"
    sbx.write_text(
        "#!/usr/bin/env bash\n"
        'printf "%s\\n" "$*" >> "$CALLS"\n'
        'case "$1" in\n'
        '  ls) printf "%s\\n" "${EXISTING_SANDBOX:-}";;\n'
        '  version) echo "sbx version v0.48.0";;\n'
        '  policy) exit "${POLICY_EXIT:-0}";;\n'
        '  exec) exit "${EXEC_EXIT:-0}";;\n'
        "esac\n"
    )
    docker = binaries / "docker"
    docker.write_text('#!/usr/bin/env bash\necho "Docker server: test"\n')
    sbx.chmod(0o755)
    docker.chmod(0o755)
    env = dict(os.environ, PATH=f"{binaries}:{os.environ['PATH']}", CALLS=str(tmp_path / "calls"))
    env["SBX_SANDBOX"] = "test-doctor"
    return repo, env


def run(host, script):
    repo, env = host
    return subprocess.run(
        ["bash", str(repo / "scripts" / script)], env=env, capture_output=True, text=True
    )


def test_create_uses_published_workload_then_policy(host):
    result = run(host, "create.sh")
    assert result.returncode == 0, result.stderr
    calls = Path(host[1]["CALLS"]).read_text()
    create = "create --name test-doctor docker.io/bandhq/band-python-kit:6.0.0"
    policy = "policy allow network --sandbox test-doctor api.anthropic.com"
    assert calls.index(create) < calls.index(policy)
    assert "\nrun " not in calls


def test_create_refuses_existing_sandbox(host):
    host[1]["EXISTING_SANDBOX"] = "test-doctor"
    result = run(host, "create.sh")
    assert result.returncode != 0
    assert "already exists" in result.stderr
    assert "\ncreate " not in Path(host[1]["CALLS"]).read_text()


def test_create_propagates_policy_failure(host):
    host[1]["POLICY_EXIT"] = "1"
    result = run(host, "create.sh")
    assert result.returncode != 0
    assert "Start the agent" not in result.stdout


def test_preflight_rejects_placeholder_identity(host):
    config = host[0] / "band.yaml"
    config.write_text(
        config.read_text().replace(
            "00000000-0000-0000-0000-000000000001", "00000000-0000-0000-0000-000000000000"
        )
    )
    assert run(host, "preflight.sh").returncode != 0


def test_verify_propagates_runtime_failure(host):
    host[1]["EXEC_EXIT"] = "1"
    assert run(host, "verify.sh").returncode != 0
