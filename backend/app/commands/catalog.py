"""Canonical catalog for Bhudi's agent command framework.

The catalog is deliberately declarative: the server describes supported operations,
while the agent owns platform-specific execution.
"""
from __future__ import annotations

from typing import Any


COMMAND_CATALOG: tuple[dict[str, Any], ...] = (
    {"type": "inventory", "name": "Inventory", "description": "Collect operating system, hardware, network, and runtime inventory.", "read_only": True},
    {"type": "processes", "name": "Processes", "description": "List running processes and their resource ownership.", "read_only": True},
    {"type": "services", "name": "Services", "description": "List installed services and service state.", "read_only": True},
    {"type": "software", "name": "Software", "description": "Enumerate installed applications and packages.", "read_only": True},
    {"type": "windows_updates", "name": "Windows Updates", "description": "Collect installed Windows updates or package update status on supported platforms.", "read_only": True},
    {"type": "event_logs", "name": "Event Logs", "description": "Read recent operating-system event or journal entries.", "read_only": True},
    {"type": "network", "name": "Network", "description": "Collect interfaces, addresses, routes, DNS, and listening sockets where supported.", "read_only": True},
    {"type": "disks", "name": "Disks", "description": "Collect mounted disks, capacity, filesystem, and utilization.", "read_only": True},
    {"type": "printers", "name": "Printers", "description": "Enumerate printers, queues, status, and default printer information.", "read_only": True},
    {"type": "remote_script", "name": "Remote Script", "description": "Execute an administrator-supplied script using an explicit interpreter.", "read_only": False, "requires_confirmation": True},
    {"type": "remote_powershell", "name": "Remote PowerShell", "description": "Execute an administrator-supplied PowerShell command on a target agent.", "read_only": False, "requires_confirmation": True},
)


def get_command_catalog() -> list[dict[str, Any]]:
    return [dict(item) for item in COMMAND_CATALOG]


def get_command_definition(command_type: str) -> dict[str, Any] | None:
    normalized = command_type.strip().lower()
    for item in COMMAND_CATALOG:
        if item["type"] == normalized:
            return dict(item)
    return None
