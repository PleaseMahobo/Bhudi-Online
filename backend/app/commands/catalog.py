"""Canonical catalog for Bhudi's agent command framework.

Each entry declares an OpenAPI-style payload_schema so UI and API clients
know required/optional fields without hard-coding command types.
"""
from __future__ import annotations

from typing import Any


def _field(
    name: str,
    *,
    type: str = "string",
    required: bool = False,
    description: str = "",
    default: Any = None,
    enum: list[Any] | None = None,
    minimum: int | float | None = None,
    maximum: int | float | None = None,
) -> dict[str, Any]:
    prop: dict[str, Any] = {
        "name": name,
        "type": type,
        "required": required,
        "description": description,
    }
    if default is not None:
        prop["default"] = default
    if enum is not None:
        prop["enum"] = enum
    if minimum is not None:
        prop["minimum"] = minimum
    if maximum is not None:
        prop["maximum"] = maximum
    return prop


COMMAND_CATALOG: tuple[dict[str, Any], ...] = (
    {
        "type": "inventory",
        "name": "Inventory",
        "description": "Collect operating system, hardware, network, and runtime inventory.",
        "read_only": True,
        "payload_schema": {"type": "object", "properties": [], "additionalProperties": False},
    },
    {
        "type": "processes",
        "name": "Processes",
        "description": "List running processes and their resource ownership.",
        "read_only": True,
        "payload_schema": {"type": "object", "properties": [], "additionalProperties": False},
    },
    {
        "type": "services",
        "name": "Services",
        "description": "List installed services and service state.",
        "read_only": True,
        "payload_schema": {"type": "object", "properties": [], "additionalProperties": False},
    },
    {
        "type": "software",
        "name": "Software",
        "description": "Enumerate installed applications and packages.",
        "read_only": True,
        "payload_schema": {"type": "object", "properties": [], "additionalProperties": False},
    },
    {
        "type": "windows_updates",
        "name": "Windows Updates",
        "description": "Collect installed Windows updates or package update status on supported platforms.",
        "read_only": True,
        "payload_schema": {"type": "object", "properties": [], "additionalProperties": False},
    },
    {
        "type": "event_logs",
        "name": "Event Logs",
        "description": "Read recent operating-system event or journal entries.",
        "read_only": True,
        "payload_schema": {
            "type": "object",
            "properties": [
                _field(
                    "log_name",
                    type="string",
                    default="Application",
                    enum=["Application", "System", "Security"],
                    description="Windows event log name (platform may map to journal on Linux).",
                ),
                _field(
                    "limit",
                    type="integer",
                    default=100,
                    minimum=1,
                    maximum=500,
                    description="Maximum number of log entries to return.",
                ),
            ],
            "additionalProperties": False,
        },
    },
    {
        "type": "network",
        "name": "Network",
        "description": "Collect interfaces, addresses, routes, DNS, and listening sockets where supported.",
        "read_only": True,
        "payload_schema": {"type": "object", "properties": [], "additionalProperties": False},
    },
    {
        "type": "disks",
        "name": "Disks",
        "description": "Collect mounted disks, capacity, filesystem, and utilization.",
        "read_only": True,
        "payload_schema": {"type": "object", "properties": [], "additionalProperties": False},
    },
    {
        "type": "printers",
        "name": "Printers",
        "description": "Enumerate printers, queues, status, and default printer information.",
        "read_only": True,
        "payload_schema": {"type": "object", "properties": [], "additionalProperties": False},
    },
    {
        "type": "endpoint_security",
        "name": "Endpoint Security Scan",
        "description": "Run an endpoint security posture scan on the target agent.",
        "read_only": True,
        "payload_schema": {"type": "object", "properties": [], "additionalProperties": False},
    },
    {
        "type": "remote_script",
        "name": "Remote Script",
        "description": "Execute an administrator-supplied script using an explicit interpreter.",
        "read_only": False,
        "requires_confirmation": True,
        "payload_schema": {
            "type": "object",
            "properties": [
                _field("script", type="string", required=True, description="Full script body to execute."),
                _field(
                    "interpreter",
                    type="string",
                    default="powershell",
                    enum=["powershell", "pwsh", "bash", "sh", "python"],
                    description="Script interpreter on the agent.",
                ),
                _field(
                    "timeout_seconds",
                    type="integer",
                    default=300,
                    minimum=5,
                    maximum=7200,
                    description="Execution timeout in seconds.",
                ),
                _field(
                    "working_directory",
                    type="string",
                    description="Optional working directory for the script process.",
                ),
            ],
            "additionalProperties": False,
        },
    },
    {
        "type": "remote_powershell",
        "name": "Remote PowerShell",
        "description": "Execute an administrator-supplied PowerShell command on a target agent.",
        "read_only": False,
        "requires_confirmation": True,
        "payload_schema": {
            "type": "object",
            "properties": [
                _field("command", type="string", required=True, description="PowerShell command text."),
                _field(
                    "timeout_seconds",
                    type="integer",
                    default=300,
                    minimum=5,
                    maximum=7200,
                    description="Execution timeout in seconds.",
                ),
                _field(
                    "arguments",
                    type="array",
                    description="Optional extra CLI arguments after -Command.",
                ),
            ],
            "additionalProperties": False,
        },
    },
)


def get_command_catalog() -> list[dict[str, Any]]:
    return [dict(item) for item in COMMAND_CATALOG]


def get_command_definition(command_type: str) -> dict[str, Any] | None:
    normalized = command_type.strip().lower()
    for item in COMMAND_CATALOG:
        if item["type"] == normalized:
            return dict(item)
    return None
