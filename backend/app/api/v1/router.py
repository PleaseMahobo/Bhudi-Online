"""API v1 router — Phase A+B: guaranteed runtime routes + best-effort enterprise routes."""
from fastapi import APIRouter

api_router = APIRouter()

# --- Always include (Phase A/B smoke path) ---
from app.api.v1.endpoints import health, devices, agent_runtime

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(devices.router, prefix="/devices", tags=["devices"])
api_router.include_router(agent_runtime.router, tags=["agent-runtime"])


def _safe_include(mod_path: str, attr: str = "router", **kwargs):
    try:
        import importlib

        mod = importlib.import_lib(mod_path) if False else importlib.import_module(mod_path)
        router = getattr(mod, attr)
        api_router.include_router(router, **kwargs)
        print(f"[router] included {mod_path}")
    except Exception as e:
        print(f"[router] skipped {mod_path}: {e}")


_safe_include("app.api.v1.endpoints.agents", tags=["agents"])
_safe_include("app.api.v1.endpoints.auth", tags=["auth"])
_safe_include("app.api.v1.endpoints.auth_extras", tags=["auth"])
_safe_include("app.api.v1.endpoints.commands", tags=["commands"])
_safe_include("app.api.v1.endpoints.command_catalog", tags=["command-catalog"])
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
_safe_include("app.api.v1.endpoints.msp", tags=["MSP"])
_safe_include("app.api.v1.endpoints.reporting", tags=["reporting"])
_safe_include("app.api.v1.endpoints.compliance", tags=["compliance"])
_safe_include("app.api.v1.endpoints.notifications", tags=["notifications"])
_safe_include("app.api.v1.endpoints.endpoint_security", tags=["endpoint-security"])
_safe_include("app.api.v1.endpoints.backup_integration", tags=["backup"])
_safe_include("app.api.v1.endpoints.psa", tags=["psa"])
_safe_include("app.api.v1.endpoints.stripe_billing", tags=["billing"])
_safe_include("app.api.v1.endpoints.telemetry", tags=["telemetry"])
_safe_include("app.api.v1.endpoints.updates", tags=["updates"])
_safe_include("app.api.v1.endpoints.inventory", tags=["inventory"])
_safe_include("app.api.v1.endpoints.ai", tags=["ai"])
_safe_include("app.api.v1.endpoints.me", tags=["me"])
_safe_include("app.api.v1.endpoints.heartbeat", tags=["heartbeat"])
