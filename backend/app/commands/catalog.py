"""Canonical catalog for Bhudi's agent command framework.

Each entry declares an OpenAPI-style payload_schema so UI and API clients
know required/optional fields without hard-coding command types.
Validation helpers enforce those schemas on POST /api/v1/commands.
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
    normalized = (command_type or "").strip().lower()
    for item in COMMAND_CATALOG:
        if item["type"] == normalized:
            return dict(item)
    return None


def known_command_types() -> list[str]:
    return [str(item["type"]) for item in COMMAND_CATALOG]


def _type_ok(expected: str, value: Any) -> bool:
    if value is None:
        return True
    t = (expected or "string").lower()
    if t == "string":
        return isinstance(value, str)
    if t in {"integer", "int"}:
        return isinstance(value, int) and not isinstance(value, bool)
    if t in {"number", "float"}:
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if t == "boolean":
        return isinstance(value, bool)
    if t == "array":
        return isinstance(value, list)
    if t == "object":
        return isinstance(value, dict)
    return True


def validate_command_payload(
    command_type: str,
    payload: dict[str, Any] | None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Validate payload against the catalog entry for command_type.

    Returns (normalized_payload, errors).
    errors is a list of FastAPI-style validation error dicts:
      {"loc": [...], "msg": "...", "type": "..."}
    When errors is non-empty, normalized_payload should not be used for queueing.
    """
    errors: list[dict[str, Any]] = []
    normalized_type = (command_type or "").strip().lower()
    definition = get_command_definition(normalized_type)

    if definition is None:
        errors.append(
            {
                "loc": ["body", "command_type"],
                "msg": (
                    f"Unknown command_type '{command_type}'. "
                    f"Known types: {', '.join(known_command_types())}"
                ),
                "type": "value_error.command_type",
            }
        )
        return {}, errors

    raw = payload if payload is not None else {}
    if not isinstance(raw, dict):
        errors.append(
            {
                "loc": ["body", "payload"],
                "msg": "payload must be an object",
                "type": "type_error.dict",
            }
        )
        return {}, errors

    schema = definition.get("payload_schema") or {}
    properties: list[dict[str, Any]] = list(schema.get("properties") or [])
    allow_extra = bool(schema.get("additionalProperties", False))
    prop_by_name = {str(p["name"]): p for p in properties if p.get("name")}

    out: dict[str, Any] = dict(raw)

    # Apply defaults for missing optional fields
    for prop in properties:
        name = str(prop["name"])
        if name not in out and "default" in prop:
            out[name] = prop["default"]

    # Required fields
    for prop in properties:
        name = str(prop["name"])
        if prop.get("required") and (name not in out or out[name] is None):
            errors.append(
                {
                    "loc": ["body", "payload", name],
                    "msg": f"Field required",
                    "type": "value_error.missing",
                }
            )
        elif prop.get("required") and isinstance(out.get(name), str) and not str(out[name]).strip():
            errors.append(
                {
                    "loc": ["body", "payload", name],
                    "msg": f"ensure this value has at least 1 character",
                    "type": "value_error.any_str.min_length",
                }
            )

    # Type / enum / range checks for present fields
    for name, value in list(out.items()):
        prop = prop_by_name.get(name)
        if prop is None:
            if not allow_extra:
                errors.append(
                    {
                        "loc": ["body", "payload", name],
                        "msg": f"Extra inputs are not permitted",
                        "type": "value_error.extra",
                    }
                )
            continue

        expected_type = str(prop.get("type") or "string")
        if value is not None and not _type_ok(expected_type, value):
            errors.append(
                {
                    "loc": ["body", "payload", name],
                    "msg": f"value is not a valid {expected_type}",
                    "type": f"type_error.{expected_type}",
                }
            )
            continue

        enum = prop.get("enum")
        if enum is not None and value is not None and value not in enum:
            errors.append(
                {
                    "loc": ["body", "payload", name],
                    "msg": f"value is not in enum {enum}",
                    "type": "value_error.const",
                }
            )

        if value is not None and isinstance(value, (int, float)) and not isinstance(value, bool):
            if prop.get("minimum") is not None and value < prop["minimum"]:
                errors.append(
                    {
                        "loc": ["body", "payload", name],
                        "msg": f"ensure this value is greater than or equal to {prop['minimum']}",
                        "type": "value_error.number.not_ge",
                    }
                )
            if prop.get("maximum") is not None and value > prop["maximum"]:
                errors.append(
                    {
                        "loc": ["body", "payload", name],
                        "msg": f"ensure this value is less than or equal to {prop['maximum']}",
                        "type": "value_error.number.not_le",
                    }
                )

    return out, errors
