"""add_asset_management_tables

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-06 02:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "vendors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("contact_name", sa.String(255), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(64), nullable=True),
        sa.Column("website", sa.String(512), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("name", name="uq_vendors_name"),
    )
    op.create_index("ix_vendors_name", "vendors", ["name"])

    op.create_table(
        "assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("devices.id", ondelete="SET NULL"), nullable=True),
        sa.Column("vendor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("asset_tag", sa.String(128), nullable=True),
        sa.Column("serial_number", sa.String(255), nullable=True),
        sa.Column("asset_type", sa.String(64), nullable=False, server_default="hardware"),
        sa.Column("category", sa.String(128), nullable=True),
        sa.Column("manufacturer", sa.String(255), nullable=True),
        sa.Column("model", sa.String(255), nullable=True),
        sa.Column("status", sa.String(64), nullable=False, server_default="in_stock"),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("assigned_to", sa.String(255), nullable=True),
        sa.Column("deployed_at", sa.Date(), nullable=True),
        sa.Column("retired_at", sa.Date(), nullable=True),
        sa.Column("warranty_provider", sa.String(255), nullable=True),
        sa.Column("warranty_start", sa.Date(), nullable=True),
        sa.Column("warranty_end", sa.Date(), nullable=True),
        sa.Column("warranty_lookup_ref", sa.String(255), nullable=True),
        sa.Column("warranty_notes", sa.Text(), nullable=True),
        sa.Column("purchase_cost", sa.Numeric(14, 2), nullable=True),
        sa.Column("currency", sa.String(8), nullable=False, server_default="ZAR"),
        sa.Column("purchase_date", sa.Date(), nullable=True),
        sa.Column("salvage_value", sa.Numeric(14, 2), nullable=True),
        sa.Column("useful_life_months", sa.Integer(), nullable=True),
        sa.Column("depreciation_method", sa.String(32), nullable=False, server_default="straight_line"),
        sa.Column("current_book_value", sa.Numeric(14, 2), nullable=True),
        sa.Column("qr_code", sa.String(128), nullable=True),
        sa.Column("qr_payload", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("specs", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("asset_tag", name="uq_assets_asset_tag"),
        sa.UniqueConstraint("qr_code", name="uq_assets_qr_code"),
    )
    op.create_index("ix_assets_tenant_id", "assets", ["tenant_id"])
    op.create_index("ix_assets_device_id", "assets", ["device_id"])
    op.create_index("ix_assets_status", "assets", ["status"])
    op.create_index("ix_assets_asset_tag", "assets", ["asset_tag"])
    op.create_index("ix_assets_serial_number", "assets", ["serial_number"])
    op.create_index("ix_assets_qr_code", "assets", ["qr_code"])
    op.create_index("ix_assets_warranty_end", "assets", ["warranty_end"])

    op.create_table(
        "software_inventory",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assets.id", ondelete="CASCADE"), nullable=True),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("devices.id", ondelete="SET NULL"), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("version", sa.String(128), nullable=True),
        sa.Column("publisher", sa.String(255), nullable=True),
        sa.Column("install_path", sa.Text(), nullable=True),
        sa.Column("install_date", sa.Date(), nullable=True),
        sa.Column("is_managed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("license_key_hint", sa.String(64), nullable=True),
        sa.Column("raw", sa.JSON(), nullable=True),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_software_inventory_asset_id", "software_inventory", ["asset_id"])
    op.create_index("ix_software_inventory_device_id", "software_inventory", ["device_id"])
    op.create_index("ix_software_inventory_name", "software_inventory", ["name"])

    op.create_table(
        "licenses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("vendor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True),
        sa.Column("product_name", sa.String(255), nullable=False),
        sa.Column("license_type", sa.String(64), nullable=False, server_default="perpetual"),
        sa.Column("seats_total", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("seats_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("license_key_encrypted", sa.Text(), nullable=True),
        sa.Column("purchase_date", sa.Date(), nullable=True),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("cost", sa.Numeric(14, 2), nullable=True),
        sa.Column("currency", sa.String(8), nullable=False, server_default="ZAR"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_licenses_tenant_id", "licenses", ["tenant_id"])
    op.create_index("ix_licenses_product_name", "licenses", ["product_name"])
    op.create_index("ix_licenses_expiry_date", "licenses", ["expiry_date"])

    op.create_table(
        "license_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("license_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("licenses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("assigned_to", sa.String(255), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_license_assignments_license_id", "license_assignments", ["license_id"])
    op.create_index("ix_license_assignments_asset_id", "license_assignments", ["asset_id"])

    op.create_table(
        "contracts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("vendor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("contract_number", sa.String(128), nullable=True),
        sa.Column("contract_type", sa.String(64), nullable=False, server_default="support"),
        sa.Column("status", sa.String(64), nullable=False, server_default="active"),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("renewal_date", sa.Date(), nullable=True),
        sa.Column("auto_renew", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("value", sa.Numeric(14, 2), nullable=True),
        sa.Column("currency", sa.String(8), nullable=False, server_default="ZAR"),
        sa.Column("terms", sa.Text(), nullable=True),
        sa.Column("document_url", sa.String(1024), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_contracts_tenant_id", "contracts", ["tenant_id"])
    op.create_index("ix_contracts_end_date", "contracts", ["end_date"])
    op.create_index("ix_contracts_status", "contracts", ["status"])

    op.create_table(
        "purchases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("vendor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("po_number", sa.String(128), nullable=True),
        sa.Column("description", sa.String(512), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("unit_cost", sa.Numeric(14, 2), nullable=True),
        sa.Column("total_cost", sa.Numeric(14, 2), nullable=True),
        sa.Column("currency", sa.String(8), nullable=False, server_default="ZAR"),
        sa.Column("purchase_date", sa.Date(), nullable=True),
        sa.Column("received_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(64), nullable=False, server_default="ordered"),
        sa.Column("invoice_ref", sa.String(128), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_purchases_tenant_id", "purchases", ["tenant_id"])
    op.create_index("ix_purchases_purchase_date", "purchases", ["purchase_date"])

    op.create_table(
        "asset_lifecycle_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("from_status", sa.String(64), nullable=True),
        sa.Column("to_status", sa.String(64), nullable=True),
        sa.Column("actor", sa.String(255), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_asset_lifecycle_events_asset_id", "asset_lifecycle_events", ["asset_id"])
    op.create_index("ix_asset_lifecycle_events_event_type", "asset_lifecycle_events", ["event_type"])


def downgrade() -> None:
    op.drop_table("asset_lifecycle_events")
    op.drop_table("purchases")
    op.drop_table("contracts")
    op.drop_table("license_assignments")
    op.drop_table("licenses")
    op.drop_table("software_inventory")
    op.drop_table("assets")
    op.drop_table("vendors")
