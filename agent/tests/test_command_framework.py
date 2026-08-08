from __future__ import annotations

from command_framework import execute_named


def test_inventory_command_returns_structured_result():
    result = execute_named("inventory")
    assert result["exit_code"] == 0
    assert "metadata" in result
    assert "data" in result["metadata"]
    assert "hostname" in result["metadata"]["data"]


def test_process_command_returns_structured_result():
    result = execute_named("processes")
    assert result["exit_code"] == 0
    assert "metadata" in result
    assert isinstance(result["metadata"]["data"], list)


def test_unsupported_command_is_rejected():
    result = execute_named("not-a-real-command")
    assert result["exit_code"] != 0
    assert "unsupported named command" in result["stderr"]


def test_remote_script_requires_script():
    result = execute_named("remote_script", {})
    assert result["exit_code"] != 0
    assert "script is required" in result["stderr"]
