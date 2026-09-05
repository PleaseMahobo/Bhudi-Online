from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints import device_management, patch_management


def _build_client() -> TestClient:
    app = FastAPI()
    app.include_router(device_management.router, prefix="/device-management")
    app.include_router(patch_management.router, prefix="/patch-management")
    return TestClient(app)


def test_device_enrollment_approval_and_grouping_flow() -> None:
    client = _build_client()

    enroll = client.post(
        "/device-management/enroll",
        json={
            "hostname": "finance-laptop",
            "platform": "windows",
            "ip": "10.0.0.42",
            "tags": ["finance", "laptop"],
        },
    )
    assert enroll.status_code == 200
    device = enroll.json()
    assert device["status"] == "pending_approval"

    discovered = client.get("/device-management/discovered")
    assert discovered.status_code == 200
    discovered_ids = [item["id"] for item in discovered.json()["devices"]]
    assert device["id"] in discovered_ids

    approved = client.post(f"/device-management/devices/{device['id']}/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    group = client.post(
        "/device-management/groups",
        json={"name": "Finance Devices", "description": "Finance team devices"},
    )
    assert group.status_code == 200

    dynamic_group = client.post(
        "/device-management/dynamic-groups",
        json={"name": "Windows Finance", "criteria": {"platform": "windows", "tags": ["finance"]}},
    )
    assert dynamic_group.status_code == 200

    tag = client.post("/device-management/tags", json={"name": "finance"})
    assert tag.status_code == 200

    policy = client.post(
        "/device-management/policies",
        json={"name": "Patch Baseline", "rules": {"approval_ring": "critical"}},
    )
    assert policy.status_code == 200

    profile = client.post(
        "/device-management/configuration-profiles",
        json={"name": "Base Security", "settings": {"encryption": True}},
    )
    assert profile.status_code == 200

    window = client.post(
        "/device-management/maintenance-windows",
        json={"name": "Nightly", "start": "22:00", "end": "23:00"},
    )
    assert window.status_code == 200


def test_patch_management_workflow_and_compliance_reporting() -> None:
    client = _build_client()

    scan = client.post(
        "/patch-management/scan",
        json={"platform": "linux", "packages": ["nginx", "openssh-server"]},
    )
    assert scan.status_code == 200
    payload = scan.json()
    assert payload["platform"] == "linux"
    assert len(payload["updates"]) >= 2

    ring = client.post(
        "/patch-management/rings",
        json={"name": "Critical", "tier": "critical"},
    )
    assert ring.status_code == 200

    rollout = client.post(
        "/patch-management/rollouts",
        json={"name": "Linux Patch Rollout", "ring_id": ring.json()["id"], "device_ids": ["device-1"]},
    )
    assert rollout.status_code == 200
    assert rollout.json()["status"] == "planned"

    execute = client.post(f"/patch-management/rollouts/{rollout.json()['id']}/execute")
    assert execute.status_code == 200
    # A rollout must not report completion when no live agent can receive it.
    assert execute.json()["status"] == "failed"
    assert execute.json()["dispatch"]["queued_count"] == 0
    assert execute.json()["dispatch"]["skipped_count"] == 1
    assert execute.json()["dispatch"]["skipped"][0]["reason"] == "agent_not_found"

    rollback = client.post(f"/patch-management/rollouts/{rollout.json()['id']}/rollback")
    assert rollback.status_code == 200
    assert rollback.json()["status"] == "rolled_back"

    compliance = client.get("/patch-management/compliance")
    assert compliance.status_code == 200
    assert compliance.json()["summary"]["total_rollouts"] >= 1
    evidence = compliance.json()["evidence"]
    assert any(item["rollout_id"] == rollout.json()["id"] for item in evidence)


def test_rollout_policy_enforcement_blocks_mismatched_rings() -> None:
    client = _build_client()

    policy = client.post(
        "/device-management/policies",
        json={"name": "Critical Only", "rules": {"approval_ring": "critical"}},
    )
    assert policy.status_code == 200

    standard_ring = client.post(
        "/patch-management/rings",
        json={"name": "Standard", "tier": "standard"},
    )
    assert standard_ring.status_code == 200

    rollout = client.post(
        "/patch-management/rollouts",
        json={"name": "Blocked Rollout", "ring_id": standard_ring.json()["id"], "device_ids": ["device-2"]},
    )
    assert rollout.status_code == 400
