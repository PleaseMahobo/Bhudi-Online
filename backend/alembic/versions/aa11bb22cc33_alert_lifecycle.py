"""Tenant-safe alert acknowledgement and resolution lifecycle."""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "aa11bb22cc33"
down_revision: Union[str, Sequence[str], None] = "f7a8b9c0d1e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("alerts", sa.Column("status", sa.String(32), nullable=False, server_default="active"))
    op.add_column("alerts", sa.Column("acknowledged_by", sa.String(255), nullable=True))
    op.add_column("alerts", sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("alerts", sa.Column("resolved_by", sa.String(255), nullable=True))
    op.add_column("alerts", sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("idx_alerts_status", "alerts", ["status"])


def downgrade() -> None:
    op.drop_index("idx_alerts_status", table_name="alerts")
    op.drop_column("alerts", "resolved_at")
    op.drop_column("alerts", "resolved_by")
    op.drop_column("alerts", "acknowledged_at")
    op.drop_column("alerts", "acknowledged_by")
    op.drop_column("alerts", "status")
