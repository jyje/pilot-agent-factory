"""Phase 3: entry-point loading, drop-in loading, and failure isolation."""

from pathlib import Path

import pytest
from agent_factory_sdk import AgentRegistry, load_dropin_agents, load_installed_agents

DROPIN_DIR = Path(__file__).parents[1] / "dropins"

GOOD_DROPIN = '''
from agent_factory_sdk import AgentManifest

class _Agent:
    manifest = AgentManifest(
        name="tmpgood", version="0.1.0", sdk_version="0.1.0", description="ok",
    )
    def build(self, config=None):
        from langchain_core.runnables import RunnablePassthrough
        return RunnablePassthrough()

AGENT = _Agent()
'''


def test_mode_a_finds_all_installed_agents():
    report = load_installed_agents()
    assert {"chitchat", "calculator", "summarizer"} <= set(report.agents)
    assert report.errors == []


def test_mode_b_loads_pirate_dropin():
    report = load_dropin_agents(DROPIN_DIR)
    assert "pirate" in report.agents
    assert report.errors == []


def test_mode_b_missing_directory_is_empty_report():
    report = load_dropin_agents("/nonexistent/path")
    assert report.agents == {} and report.errors == []


def test_broken_dropin_is_isolated(tmp_path):
    (tmp_path / "agent_good.py").write_text(GOOD_DROPIN)
    (tmp_path / "agent_broken.py").write_text("raise RuntimeError('boom at import')")
    (tmp_path / "agent_noattr.py").write_text("x = 1  # no AGENT export")

    report = load_dropin_agents(tmp_path)

    assert set(report.agents) == {"tmpgood"}
    sources = {Path(e.source).name for e in report.errors}
    assert sources == {"agent_broken.py", "agent_noattr.py"}


def test_incompatible_sdk_version_is_isolated(tmp_path):
    incompatible = GOOD_DROPIN.replace('sdk_version="0.1.0"', 'sdk_version="9.0.0"')
    (tmp_path / "agent_future.py").write_text(incompatible)

    report = load_dropin_agents(tmp_path)

    assert report.agents == {}
    assert len(report.errors) == 1
    assert "IncompatibleAgentError" in report.errors[0].error


def test_registry_merges_and_flags_duplicates(tmp_path):
    duplicate = GOOD_DROPIN.replace('name="tmpgood"', 'name="chitchat"')
    (tmp_path / "agent_dup.py").write_text(duplicate)

    registry = AgentRegistry().discover(dropin_dir=tmp_path)

    # installed chitchat wins; duplicate recorded as an error
    assert "chitchat" in registry.agents
    assert any("duplicate" in e.error for e in registry.errors)


def test_registry_get_unknown_raises_with_hint():
    registry = AgentRegistry().discover()
    with pytest.raises(KeyError, match="loaded agents"):
        registry.get("nope")
