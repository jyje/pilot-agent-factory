"""Phase 1: manifest validation and SDK compatibility rules."""

import pytest
from agent_factory_sdk import AgentManifest, IncompatibleAgentError, check_compat
from pydantic import ValidationError


def make_manifest(**overrides) -> AgentManifest:
    base = {
        "name": "demo",
        "version": "0.1.0",
        "sdk_version": "0.1.0",
        "description": "demo agent",
    }
    return AgentManifest(**(base | overrides))


def test_valid_manifest_defaults_to_messages_schema():
    m = make_manifest()
    assert m.input_schema["required"] == ["messages"]
    assert m.output_schema["required"] == ["messages"]
    assert m.capabilities == []


@pytest.mark.parametrize("bad_name", ["Demo", "1agent", "has space", ""])
def test_invalid_names_rejected(bad_name):
    with pytest.raises(ValidationError):
        make_manifest(name=bad_name)


@pytest.mark.parametrize("bad_version", ["1.0", "v1.0.0", "1.0.0-beta"])
def test_invalid_semver_rejected(bad_version):
    with pytest.raises(ValidationError):
        make_manifest(version=bad_version)


def test_compat_same_version_passes():
    check_compat(make_manifest(sdk_version="0.1.0"), sdk_version="0.1.5")


def test_compat_zero_major_minor_mismatch_fails():
    with pytest.raises(IncompatibleAgentError):
        check_compat(make_manifest(sdk_version="0.2.0"), sdk_version="0.1.0")


def test_compat_major_mismatch_fails():
    with pytest.raises(IncompatibleAgentError):
        check_compat(make_manifest(sdk_version="1.0.0"), sdk_version="2.0.0")


def test_compat_same_major_minor_drift_ok_after_1x():
    check_compat(make_manifest(sdk_version="1.2.0"), sdk_version="1.9.3")
