from __future__ import annotations

import secrets
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.asset_management import (
    Asset,
    AssetLifecycleEvent,
    Contract,
    License,
    LicenseAssignment,
    Purchase,
    SoftwareInventoryItem,
    Vendor,
)
from app.schemas.asset_management import (
    AssetCreate,
    AssetUpdate,
    ContractCreate,
    ContractUpdate,
    DepreciationResponse,
    LicenseAssignmentCreate,
    LicenseCreate,
    LicenseUpdate,
    PurchaseCreate,
    PurchaseUpdate,
    QrCodeResponse,
    SoftwareItemCreate,
    SoftwareItemUpdate,
    StatusChangeRequest,
    VendorCreate,
    VendorUpdate,
    WarrantyLookupResponse,
)


class AssetService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ---------- helpers ----------

    def _log_lifecycle(
        self,
        asset_id: UUID,
        event_type: str,
        *,
        from_status: str | None = None,
        to_status: str | None = None,
        actor: str | None = None,
        detail: str | None = None,
        metadata: dict | None = None,
    ) -> AssetLifecycleEvent:
        event = AssetLifecycleEvent(
            asset_id=asset_id,
            event_type=event_type,
            from_status=from_status,
            to_status=to_status,
            actor=actor,
            detail=detail,
            metadata_json=metadata,
        )
        self.db.add(event)
        return event

    @staticmethod
    def compute_book_value(asset: Asset, as_of: date | None = None) -> Decimal | None:
        if asset.purchase_cost is None or asset.purchase_date is None:
            return asset.current_book_value
        if asset.depreciation_method == "none":
            return asset.purchase_cost

        as_of = as_of or date.today()
        salvage = asset.salvage_value or Decimal("0")
        cost = Decimal(asset.purchase_cost)
        life = asset.useful_life_months or 36
        if life <= 0:
            return salvage

        months = (as_of.year - asset.purchase_date.year) * 12 + (
            as_of.month - asset.purchase_date.month
        )
        months = max(0, min(months, life))

        if asset.depreciation_method == "declining_balance":
            # Double-declining balance simplified per-month rate
            rate = Decimal("2") / Decimal(life)
            value = cost
            for _ in range(months):
                value = value - (value * rate)
                if value < salvage:
                    value = salvage
                    break
            return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # straight_line (default)
        depreciable = cost - salvage
        monthly = depreciable / Decimal(life)
        book = cost - (monthly * Decimal(months))
        if book < salvage:
            book = salvage
        return book.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def refresh_book_value(self, asset: Asset) -> Asset:
        asset.current_book_value = self.compute_book_value(asset)
        return asset

    @staticmethod
    def warranty_active(asset: Asset, as_of: date | None = None) -> bool:
        as_of = as_of or date.today()
        if asset.warranty_end is None:
            return False
        start_ok = asset.warranty_start is None or asset.warranty_start <= as_of
        return start_ok and asset.warranty_end >= as_of

    # ---------- Vendor ----------

    def create_vendor(self, payload: VendorCreate) -> Vendor:
        data = payload.model_dump(by_alias=False)
        # map optional metadata field
        if "metadata" in data:
            data["metadata_json"] = data.pop("metadata")
        vendor = Vendor(**{k: v for k, v in data.items() if hasattr(Vendor, k)})
        self.db.add(vendor)
        self.db.commit()
        self.db.refresh(vendor)
        return vendor

    def list_vendors(self, active_only: bool = False) -> list[Vendor]:
        q = self.db.query(Vendor)
        if active_only:
            q = q.filter(Vendor.is_active.is_(True))
        return q.order_by(Vendor.name.asc()).all()

    def get_vendor(self, vendor_id: UUID) -> Vendor | None:
        return self.db.get(Vendor, vendor_id)

    def update_vendor(self, vendor_id: UUID, payload: VendorUpdate) -> Vendor | None:
        vendor = self.get_vendor(vendor_id)
        if not vendor:
            return None
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(vendor, k, v)
        self.db.commit()
        self.db.refresh(vendor)
        return vendor

    def delete_vendor(self, vendor_id: UUID) -> bool:
        vendor = self.get_vendor(vendor_id)
        if not vendor:
            return False
        self.db.delete(vendor)
        self.db.commit()
        return True

    # ---------- Asset ----------

    def create_asset(self, payload: AssetCreate, actor: str | None = None) -> Asset:
        asset = Asset(**payload.model_dump())
        self.refresh_book_value(asset)
        # Auto QR code identity
        asset.qr_code = f"AST-{secrets.token_hex(6).upper()}"
        asset.qr_payload = f"bhudi://asset/{asset.qr_code}"
        self.db.add(asset)
        self.db.flush()
        self._log_lifecycle(
            asset.id,
            "created",
            to_status=asset.status,
            actor=actor,
            detail="Asset created",
        )
        self.db.commit()
        self.db.refresh(asset)
        return asset

    def list_assets(
        self,
        *,
        tenant_id: UUID | None = None,
        status: str | None = None,
        device_id: UUID | None = None,
    ) -> list[Asset]:
        q = self.db.query(Asset)
        if tenant_id:
            q = q.filter(Asset.tenant_id == tenant_id)
        if status:
            q = q.filter(Asset.status == status)
        if device_id:
            q = q.filter(Asset.device_id == device_id)
        return q.order_by(Asset.updated_at.desc()).all()

    def get_asset(self, asset_id: UUID) -> Asset | None:
        return self.db.get(Asset, asset_id)

    def get_asset_by_qr(self, qr_code: str) -> Asset | None:
        return self.db.query(Asset).filter(Asset.qr_code == qr_code).first()

    def update_asset(
        self, asset_id: UUID, payload: AssetUpdate, actor: str | None = None
    ) -> Asset | None:
        asset = self.get_asset(asset_id)
        if not asset:
            return None
        data = payload.model_dump(exclude_unset=True)
        old_status = asset.status
        for k, v in data.items():
            setattr(asset, k, v)
        self.refresh_book_value(asset)
        if "status" in data and data["status"] != old_status:
            self._log_lifecycle(
                asset.id,
                "status_change",
                from_status=old_status,
                to_status=asset.status,
                actor=actor,
            )
        self.db.commit()
        self.db.refresh(asset)
        return asset

    def change_status(
        self, asset_id: UUID, payload: StatusChangeRequest
    ) -> Asset | None:
        asset = self.get_asset(asset_id)
        if not asset:
            return None
        old = asset.status
        asset.status = payload.status
        if payload.status == "deployed" and asset.deployed_at is None:
            asset.deployed_at = date.today()
        if payload.status in ("retired", "disposed") and asset.retired_at is None:
            asset.retired_at = date.today()
        self._log_lifecycle(
            asset.id,
            "status_change",
            from_status=old,
            to_status=asset.status,
            actor=payload.actor,
            detail=payload.detail,
        )
        self.db.commit()
        self.db.refresh(asset)
        return asset

    def delete_asset(self, asset_id: UUID) -> bool:
        asset = self.get_asset(asset_id)
        if not asset:
            return False
        self.db.delete(asset)
        self.db.commit()
        return True

    def warranty_lookup(self, asset_id: UUID) -> WarrantyLookupResponse | None:
        asset = self.get_asset(asset_id)
        if not asset:
            return None
        active = self.warranty_active(asset)
        days = None
        if asset.warranty_end:
            days = (asset.warranty_end - date.today()).days
        return WarrantyLookupResponse(
            asset_id=asset.id,
            serial_number=asset.serial_number,
            warranty_provider=asset.warranty_provider,
            warranty_start=asset.warranty_start,
            warranty_end=asset.warranty_end,
            warranty_lookup_ref=asset.warranty_lookup_ref,
            warranty_active=active,
            days_remaining=days,
            notes=asset.warranty_notes,
        )

    def depreciation(self, asset_id: UUID) -> DepreciationResponse | None:
        asset = self.get_asset(asset_id)
        if not asset:
            return None
        book = self.compute_book_value(asset)
        asset.current_book_value = book
        self.db.commit()

        months = None
        if asset.purchase_date:
            months = (date.today().year - asset.purchase_date.year) * 12 + (
                date.today().month - asset.purchase_date.month
            )
            months = max(0, months)

        accum = None
        if asset.purchase_cost is not None and book is not None:
            accum = Decimal(asset.purchase_cost) - book

        return DepreciationResponse(
            asset_id=asset.id,
            method=asset.depreciation_method,
            purchase_cost=asset.purchase_cost,
            salvage_value=asset.salvage_value,
            useful_life_months=asset.useful_life_months,
            purchase_date=asset.purchase_date,
            months_elapsed=months,
            current_book_value=book,
            accumulated_depreciation=accum,
        )

    def ensure_qr(self, asset_id: UUID) -> QrCodeResponse | None:
        asset = self.get_asset(asset_id)
        if not asset:
            return None
        if not asset.qr_code:
            asset.qr_code = f"AST-{secrets.token_hex(6).upper()}"
            asset.qr_payload = f"bhudi://asset/{asset.qr_code}"
            self._log_lifecycle(asset.id, "qr_generated", detail=asset.qr_code)
            self.db.commit()
            self.db.refresh(asset)
        return QrCodeResponse(
            asset_id=asset.id, qr_code=asset.qr_code, qr_payload=asset.qr_payload or ""
        )

    def list_lifecycle(self, asset_id: UUID) -> list[AssetLifecycleEvent]:
        return (
            self.db.query(AssetLifecycleEvent)
            .filter(AssetLifecycleEvent.asset_id == asset_id)
            .order_by(AssetLifecycleEvent.created_at.desc())
            .all()
        )

    # ---------- Software ----------

    def create_software(self, payload: SoftwareItemCreate) -> SoftwareInventoryItem:
        item = SoftwareInventoryItem(**payload.model_dump())
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def list_software(
        self,
        *,
        asset_id: UUID | None = None,
        device_id: UUID | None = None,
    ) -> list[SoftwareInventoryItem]:
        q = self.db.query(SoftwareInventoryItem)
        if asset_id:
            q = q.filter(SoftwareInventoryItem.asset_id == asset_id)
        if device_id:
            q = q.filter(SoftwareInventoryItem.device_id == device_id)
        return q.order_by(SoftwareInventoryItem.name.asc()).all()

    def update_software(
        self, item_id: UUID, payload: SoftwareItemUpdate
    ) -> SoftwareInventoryItem | None:
        item = self.db.get(SoftwareInventoryItem, item_id)
        if not item:
            return None
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(item, k, v)
        self.db.commit()
        self.db.refresh(item)
        return item

    def delete_software(self, item_id: UUID) -> bool:
        item = self.db.get(SoftwareInventoryItem, item_id)
        if not item:
            return False
        self.db.delete(item)
        self.db.commit()
        return True

    # ---------- License ----------

    def create_license(self, payload: LicenseCreate) -> License:
        lic = License(**payload.model_dump())
        self.db.add(lic)
        self.db.commit()
        self.db.refresh(lic)
        return lic

    def list_licenses(self, active_only: bool = False) -> list[License]:
        q = self.db.query(License)
        if active_only:
            q = q.filter(License.is_active.is_(True))
        return q.order_by(License.product_name.asc()).all()

    def get_license(self, license_id: UUID) -> License | None:
        return self.db.get(License, license_id)

    def update_license(
        self, license_id: UUID, payload: LicenseUpdate
    ) -> License | None:
        lic = self.get_license(license_id)
        if not lic:
            return None
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(lic, k, v)
        self.db.commit()
        self.db.refresh(lic)
        return lic

    def delete_license(self, license_id: UUID) -> bool:
        lic = self.get_license(license_id)
        if not lic:
            return False
        self.db.delete(lic)
        self.db.commit()
        return True

    def assign_license(self, payload: LicenseAssignmentCreate) -> LicenseAssignment:
        lic = self.get_license(payload.license_id)
        if not lic:
            raise ValueError("License not found")
        if lic.seats_used >= lic.seats_total:
            raise ValueError("No seats available")
        assignment = LicenseAssignment(
            license_id=payload.license_id,
            asset_id=payload.asset_id,
            assigned_to=payload.assigned_to,
            notes=payload.notes,
        )
        lic.seats_used = (lic.seats_used or 0) + 1
        self.db.add(assignment)
        self.db.commit()
        self.db.refresh(assignment)
        return assignment

    # ---------- Contract ----------

    def create_contract(self, payload: ContractCreate) -> Contract:
        c = Contract(**payload.model_dump())
        self.db.add(c)
        self.db.commit()
        self.db.refresh(c)
        return c

    def list_contracts(self, status: str | None = None) -> list[Contract]:
        q = self.db.query(Contract)
        if status:
            q = q.filter(Contract.status == status)
        return q.order_by(Contract.end_date.asc().nullslast()).all()

    def get_contract(self, contract_id: UUID) -> Contract | None:
        return self.db.get(Contract, contract_id)

    def update_contract(
        self, contract_id: UUID, payload: ContractUpdate
    ) -> Contract | None:
        c = self.get_contract(contract_id)
        if not c:
            return None
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(c, k, v)
        self.db.commit()
        self.db.refresh(c)
        return c

    def delete_contract(self, contract_id: UUID) -> bool:
        c = self.get_contract(contract_id)
        if not c:
            return False
        self.db.delete(c)
        self.db.commit()
        return True

    # ---------- Purchase ----------

    def create_purchase(self, payload: PurchaseCreate) -> Purchase:
        data = payload.model_dump()
        if data.get("total_cost") is None and data.get("unit_cost") is not None:
            data["total_cost"] = Decimal(data["unit_cost"]) * Decimal(data.get("quantity") or 1)
        p = Purchase(**data)
        self.db.add(p)
        self.db.commit()
        self.db.refresh(p)
        return p

    def list_purchases(self) -> list[Purchase]:
        return self.db.query(Purchase).order_by(Purchase.purchase_date.desc().nullslast()).all()

    def get_purchase(self, purchase_id: UUID) -> Purchase | None:
        return self.db.get(Purchase, purchase_id)

    def update_purchase(
        self, purchase_id: UUID, payload: PurchaseUpdate
    ) -> Purchase | None:
        p = self.get_purchase(purchase_id)
        if not p:
            return None
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(p, k, v)
        self.db.commit()
        self.db.refresh(p)
        return p

    def delete_purchase(self, purchase_id: UUID) -> bool:
        p = self.get_purchase(purchase_id)
        if not p:
            return False
        self.db.delete(p)
        self.db.commit()
        return True
