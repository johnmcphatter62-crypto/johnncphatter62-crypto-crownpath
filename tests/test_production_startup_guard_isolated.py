"""Fail-closed production startup checks with synthetic environment values only."""
import pytest

from crownpath.startup_guard import (
    REQUIRED_PRODUCTION_ENV_VARS,
    REQUIRED_PRODUCTION_FLAGS,
    validate_startup,
)


def _synthetic_production_settings(monkeypatch):
    monkeypatch.setenv("CROWNPATH_ENV", "production")
    for name in REQUIRED_PRODUCTION_ENV_VARS:
        monkeypatch.setenv(name, "synthetic-test-value-not-a-secret")
    for name, expected in REQUIRED_PRODUCTION_FLAGS.items():
        monkeypatch.setenv(name, expected)


def test_production_startup_rejects_missing_required_configuration(monkeypatch):
    _synthetic_production_settings(monkeypatch)
    for name in REQUIRED_PRODUCTION_ENV_VARS:
        with monkeypatch.context() as isolated:
            isolated.delenv(name)
            with pytest.raises(RuntimeError, match="production startup blocked"):
                validate_startup()


@pytest.mark.parametrize("name", list(REQUIRED_PRODUCTION_FLAGS))
def test_production_startup_rejects_unsafe_release_flag(monkeypatch, name):
    _synthetic_production_settings(monkeypatch)
    monkeypatch.setenv(name, "false" if REQUIRED_PRODUCTION_FLAGS[name] == "true" else "true")
    with pytest.raises(RuntimeError, match="production startup blocked"):
        validate_startup()


def test_production_startup_allows_only_fully_configured_synthetic_environment(monkeypatch):
    _synthetic_production_settings(monkeypatch)
    result = validate_startup()
    assert result == {"environment": "production", "production_guard": "PASSED"}


def test_development_mode_does_not_claim_production_guard_passed(monkeypatch):
    monkeypatch.setenv("CROWNPATH_ENV", "development")
    result = validate_startup()
    assert result["production_guard"] == "NOT_REQUIRED"
    assert result["environment"] == "development"
