"""Deep Buddy RMM — client/site tree and fleet helpers."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db

router = APIRouter(prefix="/deep-buddy", tags=["Deep Buddy"])

_SEED_TREE = [
    {
        "id": "seed-c1",
        "name": "Acme MSP Lab",
        "org_type": "client",
        "source": "seed",
        "sites": [
            {"id": "seed-s1", "name": "HQ — Main", "agent_count": 0, "agents": []},
            {"id": "seed-s2", "name": "Remote Office", "agent_count": 0, "agents": []},
        ],
    },
    {
        "id": "seed-c2",
        "name": "Northwind Traders",
        "org_type": "client",
        "source": "seed",
        "sites": [
            {"id": "seed-s3", "name": "Warehouse", "agent_count": 0, "agents": []},
        ],
    },
]


def _runtime_agents() -> list[dict[str, Any]]:
    try:
        from app.api.v1.endpoints import agent_runtime

        return list(getattr(agent_runtime, "_agents", {}).values())
    except Exception:
        return []


@router.get("/tree")
def client_site_tree(db: Session = Depends(get_db)):
    """Tactical-style client → site → agent tree."""
    agents = _runtime_agents()
    tree: list[dict[str, Any]] = []
    source = "seed"

    try:
        from app.services.msp_service import MspService

        svc = MspService(db)
        orgs = svc.list_organizations(org_type="client") or svc.list_organizations()
        if orgs:
            source = "db"
            for org in orgs:
                org_id = str(getattr(org, "id", ""))
                sites_out: list[dict[str, Any]] = []
                try:
                    sites = svc.list_sites(organization_id=getattr(org, "id", None)) or []
                except TypeError:
                    sites = svc.list_sites() or []
                    sites = [
                        s
                        for s in sites
                        if str(getattr(s, "organization_id", "")) == org_id
                    ]
                for site in sites:
                    site_id = str(getattr(site, "id", ""))
                    site_agents = [
                        a for a in agents if str(a.get("site_id") or "") == site_id
                    ]
                    sites_out.append(
                        {
                            "id": site_id,
                            "name": getattr(site, "name", "Site"),
                            "agent_count": len(site_agents),
                            "agents": [
                                {
                                    "agent_id": a.get("agent_id"),
                                    "hostname": a.get("hostname"),
                                    "status": a.get("status"),
                                    "platform": a.get("platform"),
                                }
                                for a in site_agents
                            ],
                        }
                    )
                org_only = [
                    a
                    for a in agents
                    if str(a.get("organization_id") or "") == org_id and not a.get("site_id")
                ]
                if org_only:
                    sites_out.append(
                        {
                            "id": f"{org_id}-unassigned",
                            "name": "Unassigned",
                            "agent_count": len(org_only),
                            "agents": [
                                {
                                    "agent_id": a.get("agent_id"),
                                    "hostname": a.get("hostname"),
                                    "status": a.get("status"),
                                    "platform": a.get("platform"),
                                }
                                for a in org_only
                            ],
                        }
                    )
                tree.append(
                    {
                        "id": org_id,
                        "name": getattr(org, "name", "Client"),
                        "org_type": getattr(org, "org_type", "client"),
                        "source": "db",
                        "sites": sites_out,
                    }
                )
    except Exception as exc:
        print(f"[deep-buddy] tree db path failed: {exc}")

    if not tree:
        unassigned = [
            a for a in agents if not a.get("organization_id") and not a.get("site_id")
        ]
        tree = [dict(x) for x in _SEED_TREE]
        if unassigned:
            tree.insert(
                0,
                {
                    "id": "runtime-unassigned",
                    "name": "Unassigned agents",
                    "org_type": "internal",
                    "source": "runtime",
                    "sites": [
                        {
                            "id": "runtime-all",
                            "name": "All enrolled",
                            "agent_count": len(unassigned),
                            "agents": [
                                {
                                    "agent_id": a.get("agent_id"),
                                    "hostname": a.get("hostname"),
                                    "status": a.get("status"),
                                    "platform": a.get("platform"),
                                }
                                for a in unassigned
                            ],
                        }
                    ],
                },
            )
        source = "seed+runtime" if unassigned else "seed"

    total_agents = sum(s.get("agent_count", 0) for c in tree for s in c.get("sites") or [])
    return {
        "source": source,
        "clients": tree,
        "counts": {
            "clients": len(tree),
            "sites": sum(len(c.get("sites") or []) for c in tree),
            "agents_in_tree": total_agents,
            "runtime_agents": len(agents),
        },
    }


@router.get("/status")
def deep_buddy_status():
    agents = _runtime_agents()
    online = sum(1 for a in agents if str(a.get("status") or "").lower() == "online")
    return {
        "product": "Deep Buddy",
        "parent": "Cyber Bastion",
        "runtime_agents": len(agents),
        "online": online,
        "docs": "/deep-buddy",
        "console": "/deep-buddy/console",
    }
