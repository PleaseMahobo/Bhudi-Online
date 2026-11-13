"""Catalog-backed payload validation for POST /api/v1/commands."""
from __future__ import annotations

from app.commands.catalog import validate_command_payload


def test_unknown_command_type():
    payload, errors = validate_command_payload("not_a_real_type", {})
    assert payload == {}
    assert any(e["loc"][-1] == "command_type" for e in errors)


def test_empty_payload_ok_for_inventory():
    payload, errors = validate_command_payload("inventory", {})
    assert errors == []
    assert payload == {}


def test_inventory_rejects_extra_fields():
    _, errors = validate_command_payload("inventory", {"foo": 1})
    assert any(e["loc"][-1] == "foo" for e in errors)


def test_remote_script_requires_script():
    _, errors = validate_command_payload("remote_script", {"interpreter": "bash"})
    assert any(e["loc"][-1] == "script" for e in errors)


def test_remote_script_accepts_valid():
    payload, errors = validate_command_payload(
        "remote_script",
        {"script": "echo hi", "interpreter": "bash"},
    )
    assert errors == []
    assert payload["script"] == "echo hi"
    assert payload["interpreter"] == "bash"
    assert payload.get("timeout_seconds") == 300  # default applied


def test_remote_powershell_requires_command():
    _, errors = validate_command_payload("remote_powershell", {})
    assert any(e["loc"][-1] == "command" for e in errors)


def test_event_logs_defaults_and_range():
    payload, errors = validate_command_payload("event_logs", {})
    assert errors == []
    assert payload["log_name"] == "Application"
    assert payload["limit"] == 100

    _, errors_hi = validate_command_payload("event_logs", {"limit": 9999})
    assert any(e["loc"][-1] == "limit" for e in errors_hi)


def test_event_logs_enum():
    _, errors = validate_command_payload("event_logs", {"log_name": "NotALog"})
    assert any(e["loc"][-1] == "log_name" for e in errors)


def test_case_insensitive_command_type():
    payload, errors = validate_command_payload("Inventory", None)
    assert errors == []
    assert payload == {}
