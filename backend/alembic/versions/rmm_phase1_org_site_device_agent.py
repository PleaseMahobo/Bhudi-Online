"""phase 1 — canonical RMM organization/site/device/agent hierarchy

Revision ID: rmm_phase1_org_site_device_agent
Revises: m7n8o9p0q1r2
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "rmm_phase1_org_site_device_agent"
down_revision: Union[str, Sequence[str], None] = "m7n8o9p0q1r2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Device is the canonical RMM resource under an MSP organization/site.
    op.add_column(
        "devices",
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.add_column(
        "devices",
        sa.Column(
            "site_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_devices_organization_id",
        "devices",
        ["organization_id"],
    )
    op.create_index("ix_devices_site_id", "devices", ["site_id"])
    op.create_foreign_key(
        "fk_devices_organization_id_organizations",
        "devices",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_devices_site_id_sites",
        "devices",
        "sites",
        ["site_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Agent is the runtime identity/capability attached to exactly one Device.
    op.add_column(
        "agents",
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.add_column(
        "agents",
        sa.Column(
            "site_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_agents_organization_id",
        "agents",
        ["organization_id"],
    )
    op.create_index("ix_agents_site_id", "agents", ["site_id"])
    op.create_foreign_key(
        "fk_agents_organization_id_organizations",
        "agents",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_agents_site_id_sites",
        "agents",
        "sites",
        ["site_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Preserve existing tenant-scoped data by deriving the organization from
    # the tenant's 1:1 organization record, then inheriting site from device.
    op.execute(
        """
        UPDATE devices d
        SET organization_id = o.id
        FROM organizations o
        WHERE d.organization_id IS NULL
          AND d.tenant_id = o.tenant_id
        """
    )
    op.execute(
        """
        UPDATE agents a
        SET organization_id = d.organization_id,
            site_id = d.site_id
        FROM devices d
        WHERE a.device_id = d.id
          AND (a.organization_id IS NULL OR a.site_id IS NULL)
        """
    )
    op.execute(
        """
        UPDATE agents a
        SET organization_id = o.id
        FROM organizations o
        WHERE a.organization_id IS NULL
          AND a.tenant_id = o.tenant_id
        """
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_agents_site_id_sites",
        "agents",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_agents_organization_id_organizations",
        "agents",
        type_="foreignkey",
    )
    op.drop_index("ix_agents_site_id", table_name="agents")
    op.drop_index("ix_agents_organization_id", table_name="agents")
    op.drop_column("agents", "site_id")
    op.drop_column("agents", "organization_id")

    op.drop_constraint(
        "fk_devices_site_id_sites",
        "devices",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_devices_organization_id_organizations",
        "devices",
        type_="foreignkey",
    )
    op.drop_index("ix_devices_site_id", table_name="devices")
    op.drop_index("ix_devices_organization_id", table_name="devices")
    op.drop_column("devices", "site_id")
    op.drop_column("devices", "organization_id")
