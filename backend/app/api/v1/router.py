"""API v1 router — tenant-safe runtime and enterprise routes."""
from fastapi import APIRouter

api_router = APIRouter()
from app.api.v1.endpoints import health, devices, agent_runtime, agent_runtime_enrollment, agent_enrollment_portal, agent_runtime_portal

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(devices.router, prefix="/devices", tags=["devices"])
api_router.include_router(agent_runtime_enrollment.router, tags=["agent-runtime"])
api_router.include_router(agent_runtime_portal.router, tags=["agent-runtime"])
api_router.include_router(agent_runtime.router, tags=["agent-runtime"])
api_router.include_router(agent_enrollment_portal.router, tags=["agents"])


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
_safe_include("app.api.v1.endpoints.mfa", tags=["Authentication"])
_safe_include("app.api.v1.endpoints.auth_extras", tags=["auth"])
_safe_include("app.api.v1.endpoints.billing_checkout", tags=["billing"])
_safe_include("app.api.v1.endpoints.deep_buddy", tags=["deep-buddy"])
_safe_include("app.api.v1.endpoints.device_assignment", tags=["devices"])
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
_safe_include("app.api.v1.endpoints.webrtc_ice", tags=["webrtc"])
_safe_include("app.api.v1.endpoints.device_metrics", tags=["metrics"])
_safe_include("app.api.v1.endpoints.telemetry", tags=["telemetry"])
_safe_include("app.api.v1.endpoints.alert_engine", tags=["Alert Engine"])
_safe_include("app.api.v1.endpoints.asset_management", tags=["Asset Management"])
_safe_include("app.api.v1.endpoints.itsm_secure", tags=["ITSM"])
_safe_include("app.api.v1.endpoints.itsm_extended", tags=["ITSM Extended"])
_safe_include("app.api.v1.endpoints.itsm_operational", tags=["ITSM Operations"])
_safe_include("app.api.v1.endpoints.software_deployment", tags=["Software Deployment"])
_safe_include("app.api.v1.endpoints.endpoint_security", tags=["Endpoint Security"])
_safe_include("app.api.v1.endpoints.backup_integration", tags=["Backup Integration"])
_safe_include("app.api.v1.endpoints.compliance", tags=["Compliance"])
_safe_include("app.api.v1.endpoints.reporting", tags=["Reporting"])
_safe_include("app.api.v1.endpoints.msp", tags=["MSP Multi-Tenant"])
_safe_include("app.api.v1.endpoints.stripe_billing", tags=["billing"])
_safe_include("app.api.v1.endpoints.psa", tags=["PSA Integration"])
_safe_include("app.api.v1.endpoints.notifications", tags=["Notifications"])
_safe_include("app.api.v1.endpoints.ai", tags=["AI"])
_safe_include("app.api.v1.endpoints.agent_support", tags=["Agent Support"])
