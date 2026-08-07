from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    Boolean,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# Canonical framework keys used across the platform
COMPLIANCE_FRAMEWORKS = (
    "cis",
    "iso27001",
    "pci_dss",
    "hipaa",
    "gdpr",
    "nist",
    "soc2",
)

FRAMEWORK_CATALOG: list[dict[str, str]] = [
    {"framework_key": "cis", "display_name": "CIS Controls", "version": "v8"},
    {"framework_key": "iso27001", "display_name": "ISO/IEC 27001", "version": "2022"},
    {"framework_key": "pci_dss", "display_name": "PCI DSS", "version": "4.0"},
    {"framework_key": "hipaa", "display_name": "HIPAA Security Rule", "version": "45 CFR"},
    {"framework_key": "gdpr", "display_name": "GDPR", "version": "2016/679"},
    {"framework_key": "nist", "display_name": "NIST CSF", "version": "2.0"},
    {"framework_key": "soc2", "display_name": "SOC 2", "version": "TSC 2017"},
]
