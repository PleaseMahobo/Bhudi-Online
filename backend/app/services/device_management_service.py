from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import MetaData, inspect, text
from sqlalchemy.orm import Session

from app.models.device_management import (
    ConfigurationProfile,
    DeviceGroup,
    DevicePolicy,
    DeviceTag,
    DynamicDeviceGroup,
    ManagedDevice,
    MaintenanceWindow,
    PatchRing,
    PatchRollout,
)


class DeviceManagementService:
    def __init__(self, db: Session):
        self.db = db
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        bind = self.db.get_bind()
        if bind is None:
            return

        metadata = MetaData()
        for model in [
            ManagedDevice,
            DeviceGroup,
            DynamicDeviceGroup,
            DeviceTag,
            DevicePolicy,
            ConfigurationProfile,
            MaintenanceWindow,
            PatchRing,
            PatchRollout,
        ]:
            model.__table__.to_metadata(metadata)

        metadata.create_all(bind=bind)

        if bind.dialect.name == "sqlite":
            self._ensure_sqlite_column(bind, "managed_devices", "group_id", "TEXT")

    def _ensure_sqlite_column(self, bind: Any, table_name: str, column_name: str, column_type: str) -> None:
        inspector = inspect(bind)
        try:
            existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
        except Exception:
            return

        if column_name in existing_columns:
            return

        with bind.connect() as connection:
            connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"))
            connection.commit()

    def enroll_device(self, *, hostname: str, platform: str, ip_address: str | None, tags: list[str] | None, group_id: str | None = None) -> ManagedDevice:
        group_uuid = None
        if group_id is not None:
            try:
                group_uuid = UUID(group_id)
            except ValueError:
                group_uuid = None
        if group_uuid is not None:
            group = self.db.get(DeviceGroup, group_uuid)
            if group is None:
                group_uuid = None
        device = ManagedDevice(
            hostname=hostname,
            platform=platform,
            ip_address=ip_address,
            tags=tags or [],
            status="pending_approval",
            approved=False,
            group_id=group_uuid,
        )
        self.db.add(device)
        self.db.commit()
        self.db.refresh(device)
        return device

    def approve_device(self, device_id: UUID) -> ManagedDevice | None:
        device = self.db.get(ManagedDevice, device_id)
        if device is None:
            return None
        device.status = "approved"
        device.approved = True
        self.db.commit()
        self.db.refresh(device)
        return device

    def list_discovered_devices(self) -> list[ManagedDevice]:
        return self.db.query(ManagedDevice).order_by(ManagedDevice.created_at.desc()).all()

    def create_group(self, *, name: str, description: str | None) -> DeviceGroup:
        existing = self.db.query(DeviceGroup).filter(DeviceGroup.name == name).first()
        if existing is not None:
            return existing
        group = DeviceGroup(name=name, description=description)
        self.db.add(group)
        self.db.commit()
        self.db.refresh(group)
        return group

    def create_dynamic_group(self, *, name: str, criteria: dict[str, Any]) -> DynamicDeviceGroup:
        existing = self.db.query(DynamicDeviceGroup).filter(DynamicDeviceGroup.name == name).first()
        if existing is not None:
            return existing
        group = DynamicDeviceGroup(name=name, criteria=criteria)
        self.db.add(group)
        self.db.commit()
        self.db.refresh(group)
        return group

    def create_tag(self, *, name: str) -> DeviceTag:
        existing = self.db.query(DeviceTag).filter(DeviceTag.name == name).first()
        if existing is not None:
            return existing
        tag = DeviceTag(name=name)
        self.db.add(tag)
        self.db.commit()
        self.db.refresh(tag)
        return tag

    def create_policy(self, *, name: str, rules: dict[str, Any]) -> DevicePolicy:
        existing = self.db.query(DevicePolicy).filter(DevicePolicy.name == name).first()
        if existing is not None:
            return existing
        policy = DevicePolicy(name=name, rules=rules)
        self.db.add(policy)
        self.db.commit()
        self.db.refresh(policy)
        return policy

    def create_configuration_profile(self, *, name: str, settings: dict[str, Any]) -> ConfigurationProfile:
        existing = self.db.query(ConfigurationProfile).filter(ConfigurationProfile.name == name).first()
        if existing is not None:
            return existing
        profile = ConfigurationProfile(name=name, settings=settings)
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def create_maintenance_window(self, *, name: str, start: str, end: str) -> MaintenanceWindow:
        existing = self.db.query(MaintenanceWindow).filter(MaintenanceWindow.name == name).first()
        if existing is not None:
            return existing
        window = MaintenanceWindow(name=name, start=start, end=end)
        self.db.add(window)
        self.db.commit()
        self.db.refresh(window)
        return window

    def create_patch_ring(self, *, name: str, tier: str) -> PatchRing:
        existing = self.db.query(PatchRing).filter(PatchRing.name == name).first()
        if existing is not None:
            return existing
        ring = PatchRing(name=name, tier=tier)
        self.db.add(ring)
        self.db.commit()
        self.db.refresh(ring)
        return ring

    def create_rollout(self, *, name: str, ring_id: UUID, device_ids: list[str]) -> PatchRollout:
        ring = self.db.get(PatchRing, ring_id)
        if ring is None:
            raise ValueError("patch_ring_not_found")

        policy = self.db.query(DevicePolicy).filter(DevicePolicy.name == "Critical Only").first()
        if policy is not None:
            required_ring = policy.rules.get("approval_ring")
            if required_ring and str(ring.tier).lower() != str(required_ring).lower():
                raise ValueError("policy_ring_mismatch")

        rollout = PatchRollout(name=name, ring_id=ring_id, device_ids=device_ids, status="planned")
        self.db.add(rollout)
        self.db.commit()
        self.db.refresh(rollout)
        return rollout

    def execute_rollout(self, rollout_id: UUID) -> PatchRollout | None:
        rollout = self.db.get(PatchRollout, rollout_id)
        if rollout is None:
            return None
        rollout.status = "completed"
        self.db.commit()
        self.db.refresh(rollout)
        return rollout

    def rollback_rollout(self, rollout_id: UUID) -> PatchRollout | None:
        rollout = self.db.get(PatchRollout, rollout_id)
        if rollout is None:
            return None
        rollout.status = "rolled_back"
        self.db.commit()
        self.db.refresh(rollout)
        return rollout

    def compliance_summary(self) -> dict[str, Any]:
        rollouts = self.db.query(PatchRollout).all()
        evidence = []
        for rollout in rollouts:
            evidence.append(
                {
                    "rollout_id": str(rollout.id),
                    "name": rollout.name,
                    "status": rollout.status,
                    "ring_id": str(rollout.ring_id),
                    "ring_name": rollout.ring.name if rollout.ring is not None else None,
                    "device_ids": rollout.device_ids,
                    "evidence": {
                        "device_count": len(rollout.device_ids),
                        "policy_applied": rollout.status in {"completed", "rolled_back"},
                    },
                }
            )
        return {
            "summary": {
                "total_rollouts": len(rollouts),
                "planned": sum(1 for rollout in rollouts if rollout.status == "planned"),
                "completed": sum(1 for rollout in rollouts if rollout.status == "completed"),
                "rolled_back": sum(1 for rollout in rollouts if rollout.status == "rolled_back"),
            },
            "rollouts": [
                {
                    "id": str(rollout.id),
                    "name": rollout.name,
                    "ring_id": str(rollout.ring_id),
                    "ring_name": rollout.ring.name if rollout.ring is not None else None,
                    "device_ids": rollout.device_ids,
                    "status": rollout.status,
                }
                for rollout in rollouts
            ],
            "evidence": evidence,
        }
