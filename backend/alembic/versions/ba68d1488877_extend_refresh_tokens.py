"""extend_refresh_tokens

Revision ID: abcd1234
Revises: b1b2ef38d35d
Create Date: 2026-07-30

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "abcd1234"
down_revision = "b1b2ef38d35d"
branch_labels = None
depends_on = None


def upgrade():

    op.add_column(
        "refresh_tokens",
        sa.Column("device_id", sa.String(length=255), nullable=True),
    )

    op.add_column(
        "refresh_tokens",
        sa.Column("operating_system", sa.String(length=100), nullable=True),
    )

    op.add_column(
        "refresh_tokens",
        sa.Column("browser", sa.String(length=100), nullable=True),
    )

    op.add_column(
        "refresh_tokens",
        sa.Column("browser_version", sa.String(length=50), nullable=True),
    )

    op.add_column(
        "refresh_tokens",
        sa.Column("country", sa.String(length=100), nullable=True),
    )

    op.add_column(
        "refresh_tokens",
        sa.Column("city", sa.String(length=100), nullable=True),
    )

    op.add_column(
        "refresh_tokens",
        sa.Column("login_method", sa.String(length=50), nullable=True),
    )

    op.add_column(
        "refresh_tokens",
        sa.Column(
            "risk_score",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )

    op.add_column(
        "refresh_tokens",
        sa.Column(
            "trusted_device",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    op.create_index(
        "ix_refresh_token_family_generation",
        "refresh_tokens",
        ["token_family", "generation"],
    )

    op.create_index(
        "ix_refresh_token_session_generation",
        "refresh_tokens",
        ["session_id", "generation"],
    )

    op.create_index(
        "ix_refresh_token_user_active",
        "refresh_tokens",
        ["user_id", "revoked", "expires_at"],
    )

    op.create_index(
        "ix_refresh_tokens_device_id",
        "refresh_tokens",
        ["device_id"],
    )

    op.create_index(
        "ix_refresh_tokens_replaced_by_token_id",
        "refresh_tokens",
        ["replaced_by_token_id"],
    )

    op.create_index(
        "ix_refresh_tokens_revoked",
        "refresh_tokens",
        ["revoked"],
    )


def downgrade():

    op.drop_index("ix_refresh_tokens_revoked", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_replaced_by_token_id", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_device_id", table_name="refresh_tokens")
    op.drop_index("ix_refresh_token_user_active", table_name="refresh_tokens")
    op.drop_index("ix_refresh_token_session_generation", table_name="refresh_tokens")
    op.drop_index("ix_refresh_token_family_generation", table_name="refresh_tokens")

    op.drop_column("refresh_tokens", "trusted_device")
    op.drop_column("refresh_tokens", "risk_score")
    op.drop_column("refresh_tokens", "login_method")
    op.drop_column("refresh_tokens", "city")
    op.drop_column("refresh_tokens", "country")
    op.drop_column("refresh_tokens", "browser_version")
    op.drop_column("refresh_tokens", "browser")
    op.drop_column("refresh_tokens", "operating_system")
    op.drop_column("refresh_tokens", "device_id")