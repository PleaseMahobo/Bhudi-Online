from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.asset_management import (
    AssetCreate,
    AssetResponse,
    AssetUpdate,
    ContractCreate,
    ContractResponse,
    ContractUpdate,
    DepreciationResponse,
    LicenseAssignmentCreate,
    LicenseAssignmentResponse,
    LicenseCreate,
    LicenseResponse,
    LicenseUpdate,
    LifecycleEventResponse,
    PurchaseCreate,
    PurchaseResponse,
    PurchaseUpdate,
    QrCodeResponse,
    SoftwareItemCreate,
    SoftwareItemResponse,
    SoftwareItemUpdate,
    StatusChangeRequest,
    VendorCreate,
    VendorResponse,
    VendorUpdate,
    WarrantyLookupResponse,
)
from app.services.asset_service import AssetService

router = APIRouter(prefix="/assets", tags=["Asset Management"])


def _enrich_asset(asset) -> AssetResponse:
    data = AssetResponse.model_validate(asset)
    data.warranty_active = AssetService.warranty_active(asset)
    return data


def _enrich_license(lic) -> LicenseResponse:
    data = LicenseResponse.model_validate(lic)
    data.seats_available = max(0, (lic.seats_total or 0) - (lic.seats_used or 0))
    return data


# =========================================================
# Vendors
# =========================================================

@router.post("/vendors", response_model=VendorResponse, status_code=status.HTTP_201_CREATED)
def create_vendor(payload: VendorCreate, db: Session = Depends(get_db)):
    return AssetService(db).create_vendor(payload)


@router.get("/vendors", response_model=list[VendorResponse])
def list_vendors(active_only: bool = False, db: Session = Depends(get_db)):
    return AssetService(db).list_vendors(active_only=active_only)


@router.get("/vendors/{vendor_id}", response_model=VendorResponse)
def get_vendor(vendor_id: UUID, db: Session = Depends(get_db)):
    vendor = AssetService(db).get_vendor(vendor_id)
    if not vendor:
        raise HTTPException(404, "Vendor not found")
    return vendor


@router.patch("/vendors/{vendor_id}", response_model=VendorResponse)
def update_vendor(vendor_id: UUID, payload: VendorUpdate, db: Session = Depends(get_db)):
    vendor = AssetService(db).update_vendor(vendor_id, payload)
    if not vendor:
        raise HTTPException(404, "Vendor not found")
    return vendor


@router.delete("/vendors/{vendor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vendor(vendor_id: UUID, db: Session = Depends(get_db)):
    if not AssetService(db).delete_vendor(vendor_id):
        raise HTTPException(404, "Vendor not found")


# =========================================================
# Hardware assets
# =========================================================

@router.post("", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
def create_asset(payload: AssetCreate, db: Session = Depends(get_db)):
    asset = AssetService(db).create_asset(payload)
    return _enrich_asset(asset)


@router.get("", response_model=list[AssetResponse])
def list_assets(
    tenant_id: UUID | None = None,
    status: str | None = None,
    device_id: UUID | None = None,
    db: Session = Depends(get_db),
):
    assets = AssetService(db).list_assets(
        tenant_id=tenant_id, status=status, device_id=device_id
    )
    return [_enrich_asset(a) for a in assets]


@router.get("/by-qr/{qr_code}", response_model=AssetResponse)
def get_asset_by_qr(qr_code: str, db: Session = Depends(get_db)):
    asset = AssetService(db).get_asset_by_qr(qr_code)
    if not asset:
        raise HTTPException(404, "Asset not found for QR code")
    return _enrich_asset(asset)


@router.get("/{asset_id}", response_model=AssetResponse)
def get_asset(asset_id: UUID, db: Session = Depends(get_db)):
    asset = AssetService(db).get_asset(asset_id)
    if not asset:
        raise HTTPException(404, "Asset not found")
    return _enrich_asset(asset)


@router.patch("/{asset_id}", response_model=AssetResponse)
def update_asset(asset_id: UUID, payload: AssetUpdate, db: Session = Depends(get_db)):
    asset = AssetService(db).update_asset(asset_id, payload)
    if not asset:
        raise HTTPException(404, "Asset not found")
    return _enrich_asset(asset)


@router.post("/{asset_id}/status", response_model=AssetResponse)
def change_asset_status(
    asset_id: UUID, payload: StatusChangeRequest, db: Session = Depends(get_db)
):
    asset = AssetService(db).change_status(asset_id, payload)
    if not asset:
        raise HTTPException(404, "Asset not found")
    return _enrich_asset(asset)


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asset(asset_id: UUID, db: Session = Depends(get_db)):
    if not AssetService(db).delete_asset(asset_id):
        raise HTTPException(404, "Asset not found")


@router.get("/{asset_id}/warranty", response_model=WarrantyLookupResponse)
def warranty_lookup(asset_id: UUID, db: Session = Depends(get_db)):
    result = AssetService(db).warranty_lookup(asset_id)
    if not result:
        raise HTTPException(404, "Asset not found")
    return result


@router.get("/{asset_id}/depreciation", response_model=DepreciationResponse)
def depreciation(asset_id: UUID, db: Session = Depends(get_db)):
    result = AssetService(db).depreciation(asset_id)
    if not result:
        raise HTTPException(404, "Asset not found")
    return result


@router.post("/{asset_id}/qr", response_model=QrCodeResponse)
def ensure_qr(asset_id: UUID, db: Session = Depends(get_db)):
    result = AssetService(db).ensure_qr(asset_id)
    if not result:
        raise HTTPException(404, "Asset not found")
    return result


@router.get("/{asset_id}/lifecycle", response_model=list[LifecycleEventResponse])
def list_lifecycle(asset_id: UUID, db: Session = Depends(get_db)):
    if not AssetService(db).get_asset(asset_id):
        raise HTTPException(404, "Asset not found")
    return AssetService(db).list_lifecycle(asset_id)


# =========================================================
# Software inventory
# =========================================================

@router.post(
    "/software", response_model=SoftwareItemResponse, status_code=status.HTTP_201_CREATED
)
def create_software(payload: SoftwareItemCreate, db: Session = Depends(get_db)):
    return AssetService(db).create_software(payload)


@router.get("/software", response_model=list[SoftwareItemResponse])
def list_software(
    asset_id: UUID | None = None,
    device_id: UUID | None = None,
    db: Session = Depends(get_db),
):
    return AssetService(db).list_software(asset_id=asset_id, device_id=device_id)


@router.patch("/software/{item_id}", response_model=SoftwareItemResponse)
def update_software(
    item_id: UUID, payload: SoftwareItemUpdate, db: Session = Depends(get_db)
):
    item = AssetService(db).update_software(item_id, payload)
    if not item:
        raise HTTPException(404, "Software item not found")
    return item


@router.delete("/software/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_software(item_id: UUID, db: Session = Depends(get_db)):
    if not AssetService(db).delete_software(item_id):
        raise HTTPException(404, "Software item not found")


# =========================================================
# Licenses
# =========================================================

@router.post(
    "/licenses", response_model=LicenseResponse, status_code=status.HTTP_201_CREATED
)
def create_license(payload: LicenseCreate, db: Session = Depends(get_db)):
    return _enrich_license(AssetService(db).create_license(payload))


@router.get("/licenses", response_model=list[LicenseResponse])
def list_licenses(active_only: bool = False, db: Session = Depends(get_db)):
    return [_enrich_license(l) for l in AssetService(db).list_licenses(active_only)]


@router.get("/licenses/{license_id}", response_model=LicenseResponse)
def get_license(license_id: UUID, db: Session = Depends(get_db)):
    lic = AssetService(db).get_license(license_id)
    if not lic:
        raise HTTPException(404, "License not found")
    return _enrich_license(lic)


@router.patch("/licenses/{license_id}", response_model=LicenseResponse)
def update_license(
    license_id: UUID, payload: LicenseUpdate, db: Session = Depends(get_db)
):
    lic = AssetService(db).update_license(license_id, payload)
    if not lic:
        raise HTTPException(404, "License not found")
    return _enrich_license(lic)


@router.delete("/licenses/{license_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_license(license_id: UUID, db: Session = Depends(get_db)):
    if not AssetService(db).delete_license(license_id):
        raise HTTPException(404, "License not found")


@router.post(
    "/licenses/assign",
    response_model=LicenseAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def assign_license(payload: LicenseAssignmentCreate, db: Session = Depends(get_db)):
    try:
        return AssetService(db).assign_license(payload)
    except ValueError as e:
        raise HTTPException(400, str(e))


# =========================================================
# Contracts
# =========================================================

@router.post(
    "/contracts", response_model=ContractResponse, status_code=status.HTTP_201_CREATED
)
def create_contract(payload: ContractCreate, db: Session = Depends(get_db)):
    return AssetService(db).create_contract(payload)


@router.get("/contracts", response_model=list[ContractResponse])
def list_contracts(status: str | None = None, db: Session = Depends(get_db)):
    return AssetService(db).list_contracts(status=status)


@router.get("/contracts/{contract_id}", response_model=ContractResponse)
def get_contract(contract_id: UUID, db: Session = Depends(get_db)):
    c = AssetService(db).get_contract(contract_id)
    if not c:
        raise HTTPException(404, "Contract not found")
    return c


@router.patch("/contracts/{contract_id}", response_model=ContractResponse)
def update_contract(
    contract_id: UUID, payload: ContractUpdate, db: Session = Depends(get_db)
):
    c = AssetService(db).update_contract(contract_id, payload)
    if not c:
        raise HTTPException(404, "Contract not found")
    return c


@router.delete("/contracts/{contract_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contract(contract_id: UUID, db: Session = Depends(get_db)):
    if not AssetService(db).delete_contract(contract_id):
        raise HTTPException(404, "Contract not found")


# =========================================================
# Purchases
# =========================================================

@router.post(
    "/purchases", response_model=PurchaseResponse, status_code=status.HTTP_201_CREATED
)
def create_purchase(payload: PurchaseCreate, db: Session = Depends(get_db)):
    return AssetService(db).create_purchase(payload)


@router.get("/purchases", response_model=list[PurchaseResponse])
def list_purchases(db: Session = Depends(get_db)):
    return AssetService(db).list_purchases()


@router.get("/purchases/{purchase_id}", response_model=PurchaseResponse)
def get_purchase(purchase_id: UUID, db: Session = Depends(get_db)):
    p = AssetService(db).get_purchase(purchase_id)
    if not p:
        raise HTTPException(404, "Purchase not found")
    return p


@router.patch("/purchases/{purchase_id}", response_model=PurchaseResponse)
def update_purchase(
    purchase_id: UUID, payload: PurchaseUpdate, db: Session = Depends(get_db)
):
    p = AssetService(db).update_purchase(purchase_id, payload)
    if not p:
        raise HTTPException(404, "Purchase not found")
    return p


@router.delete("/purchases/{purchase_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_purchase(purchase_id: UUID, db: Session = Depends(get_db)):
    if not AssetService(db).delete_purchase(purchase_id):
        raise HTTPException(404, "Purchase not found")
