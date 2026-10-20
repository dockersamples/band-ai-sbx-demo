"""Regression tests run without credentials, network access, or a live sandbox."""

import asyncio
import shutil
from pathlib import Path

import pytest

import main


@pytest.fixture
def fixture_copy(tmp_path, monkeypatch):
    root = tmp_path / "fixture"
    shutil.copytree(
        Path(__file__).resolve().parents[1] / "fixture",
        root,
        ignore=shutil.ignore_patterns(*main.SKIPPED_DIRS),
    )
    monkeypatch.setattr(main, "FIXTURE_ROOT", root)
    monkeypatch.setattr(main, "SOURCE_ROOT", root / "src")
    return root


def test_fixture_can_be_repaired_without_changing_tests(fixture_copy):
    tests = (fixture_copy / "tests/test_slugify.py").read_bytes()
    assert "1 failed, 3 passed" in main.run_tests()
    assert "src/slugify.py" in main.list_files()
    assert 'replace(" ", "-")' in main.read_file("src/slugify.py")
    assert main.write_source(
        "slugify.py", 'def slugify(text: str) -> str:\n    return "-".join(text.lower().split())\n'
    ).startswith("Wrote")
    assert "4 passed" in main.run_tests()
    assert (fixture_copy / "tests/test_slugify.py").read_bytes() == tests


@pytest.mark.parametrize("path", ["/etc/passwd", "../../outside.txt", ""])
def test_reads_cannot_escape_fixture(fixture_copy, path):
    assert main.read_file(path).startswith("ERROR:")


@pytest.mark.parametrize("path", ["../tests/test_slugify.py", "/tmp/new.py", "new.py"])
def test_writes_cannot_change_tests_or_create_files(fixture_copy, path):
    tests = (fixture_copy / "tests/test_slugify.py").read_bytes()
    assert main.write_source(path, "changed").startswith("ERROR:")
    assert (fixture_copy / "tests/test_slugify.py").read_bytes() == tests


def test_symlink_cannot_write_outside_source(fixture_copy, tmp_path):
    outside = tmp_path / "outside.py"
    outside.write_text("original")
    (fixture_copy / "src/link.py").symlink_to(outside)
    assert main.write_source("link.py", "changed").startswith("ERROR:")
    assert outside.read_text() == "original"


def test_output_is_bounded():
    result = main._bounded("x" * (main.MAX_OUTPUT_CHARS + 17))
    assert result.startswith("x" * main.MAX_OUTPUT_CHARS)
    assert "17 more characters" in result


@pytest.fixture
def band_environment(monkeypatch):
    monkeypatch.setenv("BAND_AGENT_ID", "00000000-0000-0000-0000-000000000001")
    monkeypatch.setenv("BAND_API_KEY", "proxy-managed")
    monkeypatch.setenv("BAND_REST_URL", "https://app.band.ai")
    monkeypatch.setenv("BAND_WS_URL", "wss://app.band.ai/api/v1/socket/websocket")


def test_missing_provider_key_has_actionable_error(band_environment, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_PROXY_KEY", raising=False)
    with pytest.raises(RuntimeError, match="Store the sandbox-scoped custom secret"):
        asyncio.run(main.main())


def test_other_provider_override_is_rejected(band_environment, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_PROXY_KEY", "sk-ant-proxy-managed")
    monkeypatch.setattr(main, "MODEL", "openai:example")
    with pytest.raises(ValueError, match="anthropic:<model-id>"):
        asyncio.run(main.main())


def test_sdk6_adapter_wiring_without_connecting(band_environment, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_PROXY_KEY", "sk-ant-proxy-managed")
    captured = {}
    sentinel = object()

    def create(**kwargs):
        captured.update(kwargs)
        return sentinel

    async def run(agent):
        assert agent is sentinel

    monkeypatch.setattr(main.Agent, "create", create)
    monkeypatch.setattr(main, "run_with_graceful_shutdown", run)
    asyncio.run(main.main())
    adapter = captured["adapter"]
    assert isinstance(adapter, main.PydanticAIAdapter)
    assert main.Emit.TOOL_CALLS in adapter.features.emit
    assert captured["api_key"] == "proxy-managed"
