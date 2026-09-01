"""reconcile production agents schema drift safely

Revision ID: m7n8o9p0q1r2
Revises: l6m7n8o9p0q1
Create Date: 2026-09-01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "m7n8o9p0q1r2"
down_revision: Union[str, Sequence[str], None] = "l6m7n8o9p0q1"
branch_labels = None
depends_on = None


def _add_if_missing(table: str, name: str, column: sa.Column) -> None:
    inspector = sa.inspect(op.get_bind())
    if name not in {c["name"] for c in inspector.get_columns(table)}:
        op.add_column(table, column)


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("agents"):
        raise RuntimeError("Production reconciliation expected existing agents table")

    cols = [
        ("device_name", sa.Text(), True, None), ("machine_guid", sa.Text(), True, None),
        ("agent_uuid", postgresql.UUID(as_uuid=True), True, None), ("agent_version", sa.Text(), True, None),
        ("agent_build", sa.Text(), True, None), ("update_channel", sa.Text(), False, sa.text("'stable'")),
        ("platform", sa.Text(), True, None), ("architecture", sa.Text(), True, None),
        ("operating_system", sa.Text(), True, None), ("os_version", sa.Text(), True, None),
        ("manufacturer", sa.Text(), True, None), ("model", sa.Text(), True, None),
        ("serial_number", sa.Text(), True, None), ("bios_serial", sa.Text(), True, None),
        ("cpu_model", sa.Text(), True, None), ("cpu_cores", sa.Integer(), True, None),
        ("memory_total_mb", sa.Integer(), True, None), ("disk_total_gb", sa.Integer(), True, None),
        ("ip_address", sa.Text(), True, None), ("ipv4_address", sa.Text(), True, None),
        ("ipv6_address", sa.Text(), True, None), ("mac_address", sa.Text(), True, None),
        ("fqdn", sa.Text(), True, None), ("domain", sa.Text(), True, None),
        ("api_key_hash", sa.Text(), True, None), ("enrollment_token", sa.Text(), True, None),
        ("enrollment_secret_hash", sa.Text(), True, None), ("registration_state", sa.Text(), False, sa.text("'pending'")),
        ("enrolled_at", postgresql.TIMESTAMP(timezone=True), True, None),
        ("approved", sa.Boolean(), False, sa.text("false")), ("approved_by", postgresql.UUID(as_uuid=True), True, None),
        ("approved_at", postgresql.TIMESTAMP(timezone=True), True, None), ("trusted", sa.Boolean(), False, sa.text("false")),
        ("trust_level", sa.Text(), False, sa.text("'trusted'")), ("secret_version", sa.Integer(), False, sa.text("1")),
        ("public_key", sa.Text(), True, None), ("certificate_thumbprint", sa.Text(), True, None),
        ("status", sa.Text(), False, sa.text("'offline'")), ("registered_at", postgresql.TIMESTAMP(timezone=True), True, None),
        ("last_seen", postgresql.TIMESTAMP(timezone=True), True, None), ("last_heartbeat", postgresql.TIMESTAMP(timezone=True), True, None),
        ("last_checkin", postgresql.TIMESTAMP(timezone=True), True, None), ("heartbeat_interval", sa.Integer(), False, sa.text("30")),
        ("poll_interval", sa.Integer(), False, sa.text("30")), ("last_ip_address", sa.Text(), True, None),
        ("last_logged_on_user", sa.Text(), True, None), ("health_score", sa.Integer(), False, sa.text("100")),
        ("enabled", sa.Boolean(), False, sa.text("true")), ("tamper_protection", sa.Boolean(), False, sa.text("false")),
        ("quarantined", sa.Boolean(), False, sa.text("false")), ("revoked", sa.Boolean(), False, sa.text("false")),
        ("revoked_at", postgresql.TIMESTAMP(timezone=True), True, None), ("revocation_reason", sa.Text(), True, None),
        ("auto_update", sa.Boolean(), False, sa.text("true")), ("update_available", sa.Boolean(), False, sa.text("false")),
        ("target_version", sa.Text(), True, None), ("last_update", postgresql.TIMESTAMP(timezone=True), True, None),
        ("command_timeout", sa.Integer(), False, sa.text("300")), ("restart_count", sa.Integer(), False, sa.text("0")),
        ("last_error", sa.Text(), True, None), ("last_error_at", postgresql.TIMESTAMP(timezone=True), True, None),
        ("tenant_id", postgresql.UUID(as_uuid=True), True, None), ("device_id", postgresql.UUID(as_uuid=True), True, None),
    ]
    for name, typ, nullable, default in cols:
        _add_if_missing("agents", name, sa.Column(name, typ, nullable=nullable, server_default=default))


def downgrade() -> None:
    # Preserve production data; this reconciliation migration is forward-only.
    pass
