"""enforce tenant ownership for agents

Revision ID: h1i2j3k4l5m6
Revises: g7h8i9j0k1l2

Backfills agent ownership from the authoritative device tenant and then makes
agents.tenant_id mandatory. The migration intentionally fails when an existing
agent cannot be assigned to a tenant instead of leaving an isolation hole.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "h1i2j3k4l5m6"
down_revision: Union[str, Sequence[str], None] = "g7h8i9j0k1l2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tenant_fk_names(bind) -> list[str]:
    return [
        fk["name"]
        for fk in sa.inspect(bind).get_foreign_keys("agents")
        if fk.get("constrained_columns") == ["tenant_id"] and fk.get("name")
    ]


def upgrade() -> None:
    bind = op.get_bind()

    bind.execute(
        sa.text(
            """
            UPDATE agents AS a
            SET tenant_id = d.tenant_id
            FROM devices AS d
            WHERE a.tenant_id IS NULL
              AND a.device_id = d.id
              AND d.tenant_id IS NOT NULL
            """
        )
    )

    unresolved = bind.execute(
        sa.text("SELECT count(*) FROM agents WHERE tenant_id IS NULL")
    ).scalar_one()
    if unresolved:
        raise RuntimeError(
            f"Refusing to enable tenant isolation: {unresolved} agent(s) have no tenant owner."
        )

    for name in _tenant_fk_names(bind):
        op.drop_constraint(name, "agents", type_="foreignkey")

    op.alter_column(
        "agents",
        "tenant_id",
        existing_type=sa.UUID(),
        nullable=False,
    )
    op.create_foreign_key(
        "fk_agents_tenant_id",
        "agents",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    bind = op.get_bind()
    for name in _tenant_fk_names(bind):
        op.drop_constraint(name, "agents", type_="foreignkey")
    op.alter_column(
        "agents",
        "tenant_id",
        existing_type=sa.UUID(),
        nullable=True,
    )
    op.create_foreign_key(
        "fk_agents_tenant_id",
        "agents",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="SET NULL",
    )
