"""API v1 router — Phase A+B: guaranteed runtime routes + best-effort enterprise routes."""
from fastapi import APIRouter

api_router = APIRouter()

# --- Always include (Phase A/B smoke path) ---
from app.api.v1.endpoints import health, devices, agent_runtime

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(devices.router, prefix="/devices", tags=["devices"])
api_router.include_router(agent_runtime.router, tags=["agent-runtime"])

# --- Best-effort enterprise routers (skip if broken imports) ---
def _safe_include(mod_path: str, attr: str = "router", **kwargs):
    try:
        import importlib
        mod = importlib.import_module(mod_path)
        router = getattr(mod, attr)
        api_router.include_router(router, **kwargs)
        print(f"[router] included {mod_path}")
    except Exception as e:
        print(f"[router] skipped {mod_path}: {e}")


_safe_include("app.api.v1.endpoints.agents", tags=["agents"])
_safe_include("app.api.v1.endpoints.auth", tags=["auth"])
_safe_include("app.api.v1.endpoints.commands", tags=["commands"])
_safe_include("app.api.v1.endpoints.agent_commands", tags=["agent-commands"])
_safe_include("app.api.v1.endpoints.rbac", tags=["rbac"])
_safe_include("app.api.v1.endpoints.audit", tags=["audit"])
_safe_include("app.api.v1.endpoints.device_management", tags=["device-management"])
_safe_include("app.api.v1.endpoints.patch_management", tags=["patch-management"])
_safe_include("app.api.v1.endpoints.monitoring", tags=["monitoring"])
_safe_include("app.api.v1.endpoints.automation", tags=["automation"])
_safe_include("app.api.v1.endpoints.remote_access", tags=["remote-access"])
_safe_include("app.api.v1.endpoints.alert_engine", tags=["Alert Engine"])
_safe_include("app.api.v1.endpoints.asset_management", tags=["Asset Management"])
_safe_include("app.api.v1.endpoints.itsm", tags=["ITSM"])
_safe_include("app.api.v1.endpoints.software_deployment", tags=["Software Deployment"])
_safe_include("app.api.v1.endpoints.endpoint_security", tags=["Endpoint Security"])
_safe_include("app.api.v1.endpoints.backup_integration", tags=["Backup Integration"])
_safe_include("app.api.v1.endpoints.compliance", tags=["Compliance"])
_safe_include("app.api.v1.endpoints.reporting", tags=["Reporting"])
_safe_include("app.api.v1.endpoints.msp", tags=["MSP Multi-Tenant"])
_safe_include("app.api.v1.endpoints.stripe_billing", tags=["Stripe Billing"])
_safe_include("app.api.v1.endpoints.psa", tags=["PSA Integration"])
_safe_include("app.api.v1.endpoints.notifications", tags=["Notifications"])
_safe_include("app.api.v1.endpoints.ai", tags=["AI"])
