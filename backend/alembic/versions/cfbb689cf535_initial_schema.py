"""initial_schema

Revision ID: cfbb689cf535
Revises:
Create Date: 2026-07-21 07:35:33.402861

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "cfbb689cf535"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # ---------------------------------------------------------
    # Refresh token storage
    # ---------------------------------------------------------

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),

        sa.Column(
            "token_hash",
            sa.String(length=64),
            nullable=False,
        ),

        sa.Column(
            "jwt_id",
            sa.String(length=64),
            nullable=False,
        ),

        sa.Column(
            "session_id",
            sa.String(length=64),
            nullable=False,
        ),

        sa.Column(
            "token_family",
            sa.String(length=64),
            nullable=False,
        ),

        sa.Column(
            "generation",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "expires_at",
            sa.DateTime(),
            nullable=False,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
        ),

        sa.Column(
            "last_used_at",
            sa.DateTime(),
            nullable=True,
        ),

        sa.Column(
            "revoked",
            sa.Boolean(),
            nullable=False,
        ),

        sa.Column(
            "revoked_at",
            sa.DateTime(),
            nullable=True,
        ),

        sa.Column(
            "revoked_reason",
            sa.String(length=100),
            nullable=True,
        ),

        sa.Column(
            "replaced_by_token_id",
            sa.UUID(),
            nullable=True,
        ),

        sa.Column(
            "ip_address",
            sa.String(length=64),
            nullable=True,
        ),

        sa.Column(
            "user_agent",
            sa.String(length=512),
            nullable=True,
        ),

        sa.Column(
            "device_name",
            sa.String(length=255),
            nullable=True,
        ),

        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_refresh_tokens_user",
            ondelete="CASCADE",
        ),

        sa.ForeignKeyConstraint(
            ["replaced_by_token_id"],
            ["refresh_tokens.id"],
            name="fk_refresh_tokens_replaced_by",
        ),

        sa.PrimaryKeyConstraint(
            "id",
            name="pk_refresh_tokens",
        ),
    )


    # ---------------------------------------------------------
    # Refresh token indexes
    # ---------------------------------------------------------

    op.create_index(
        "ix_refresh_tokens_jwt_id",
        "refresh_tokens",
        ["jwt_id"],
        unique=True,
    )

    op.create_index(
        "ix_refresh_tokens_session_id",
        "refresh_tokens",
        ["session_id"],
        unique=False,
    )

    op.create_index(
        "ix_refresh_tokens_token_family",
        "refresh_tokens",
        ["token_family"],
        unique=False,
    )

    op.create_index(
        "ix_refresh_tokens_token_hash",
        "refresh_tokens",
        ["token_hash"],
        unique=True,
    )

    op.create_index(
        "ix_refresh_tokens_user_id",
        "refresh_tokens",
        ["user_id"],
        unique=False,
    )


    # ---------------------------------------------------------
    # Existing schema corrections
    # ---------------------------------------------------------

    op.create_foreign_key(
        "fk_commands_device",
        "commands",
        "devices",
        ["device_id"],
        ["id"],
    )


    op.create_foreign_key(
        "fk_compliance_reports_tenant",
        "compliance_reports",
        "tenants",
        ["tenant_id"],
        ["id"],
    )


    op.create_foreign_key(
        "fk_device_metrics_tenant",
        "device_metrics",
        "tenants",
        ["tenant_id"],
        ["id"],
    )


    op.drop_constraint(
        "profiles_id_fkey",
        "profiles",
        type_="foreignkey",
    )


    op.create_foreign_key(
        "fk_profiles_user",
        "profiles",
        "users",
        ["id"],
        ["id"],
        ondelete="CASCADE",
    )


    op.create_foreign_key(
        "fk_users_tenant",
        "users",
        "tenants",
        ["tenant_id"],
        ["id"],
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_constraint(
        "fk_users_tenant",
        "users",
        type_="foreignkey",
    )


    op.drop_constraint(
        "fk_profiles_user",
        "profiles",
        type_="foreignkey",
    )


    op.create_foreign_key(
        "profiles_id_fkey",
        "profiles",
        "users",
        ["id"],
        ["id"],
        ondelete="CASCADE",
    )


    op.drop_constraint(
        "fk_device_metrics_tenant",
        "device_metrics",
        type_="foreignkey",
    )


    op.drop_constraint(
        "fk_compliance_reports_tenant",
        "compliance_reports",
        type_="foreignkey",
    )


    op.drop_constraint(
        "fk_commands_device",
        "commands",
        type_="foreignkey",
    )


    op.drop_index(
        "ix_refresh_tokens_user_id",
        table_name="refresh_tokens",
    )

    op.drop_index(
        "ix_refresh_tokens_token_hash",
        table_name="refresh_tokens",
    )

    op.drop_index(
        "ix_refresh_tokens_token_family",
        table_name="refresh_tokens",
    )

    op.drop_index(
        "ix_refresh_tokens_session_id",
        table_name="refresh_tokens",
    )

    op.drop_index(
        "ix_refresh_tokens_jwt_id",
        table_name="refresh_tokens",
    )


    op.drop_table(
        "refresh_tokens",
    )