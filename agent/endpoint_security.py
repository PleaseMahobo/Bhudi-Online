"""Endpoint security product detection for Bhudi RMM agents.

Windows-first detection of installed AV/EDR products and their health status.
Results are designed to be posted to POST /api/v1/endpoint-security/ingest/agent.
"""
from __future__ import annotations

import json
import os
import platform
import re
import socket
import subprocess
from datetime import datetime, timezone
from typing import Any


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_ps(script: str, timeout: int = 45) -> tuple[int, str, str]:
    """Run a PowerShell script and return (exit_code, stdout, stderr)."""
    try:
        p = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                script,
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"
    except Exception as exc:
        return 1, "", str(exc)


def _run(cmd: list[str], timeout: int = 30) -> tuple[int, str, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()
    except Exception as e:
        return 1, "", str(e)


def _service_state(service_name: str) -> dict[str, Any]:
    """Query a Windows service by name."""
    code, out, err = _run(["sc", "query", service_name])
    state = "not_found"
    if code == 0 and out:
        m = re.search(r"STATE\s+:\s+\d+\s+(\w+)", out)
        if m:
            state = m.group(1).lower()  # running | stopped | ...
    return {"name": service_name, "state": state, "raw_exit": code}


def _reg_value(path: str, name: str) -> str | None:
    """Read a registry value via reg.exe (HKLM)."""
    code, out, _ = _run(["reg", "query", path, "/v", name])
    if code != 0 or not out:
        return None
    # Format:    Name    REG_SZ    Value
    for line in out.splitlines():
        if name.lower() in line.lower() and "REG_" in line:
            parts = line.split(None, 3)
            if len(parts) >= 4:
                return parts[3].strip()
    return None


def _product_installed_via_uninstall(display_name_patterns: list[str]) -> dict[str, Any]:
    """Check Uninstall keys for a product."""
    script = r"""
$patterns = @({patterns})
$paths = @(
  'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*',
  'HKLM:\Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*'
)
Get-ItemProperty $paths -ErrorAction SilentlyContinue |
  Where-Object { $_.DisplayName -and ($patterns | Where-Object { $_.DisplayName -like $_ }) } |
  Select-Object DisplayName, DisplayVersion, Publisher, InstallDate |
  ConvertTo-Json -Compress
""".replace("{patterns}", ", ".join(f"'{p}'" for p in display_name_patterns))
    code, out, err = _run_ps(script)
    if code != 0 or not out:
        return {"installed": False}
    try:
        data = json.loads(out)
        if isinstance(data, dict):
            data = [data]
        if not data:
            return {"installed": False}
        first = data[0]
        return {
            "installed": True,
            "display_name": first.get("DisplayName"),
            "version": first.get("DisplayVersion"),
            "publisher": first.get("Publisher"),
            "install_date": first.get("InstallDate"),
        }
    except Exception:
        return {"installed": False, "raw": out[:500]}


# ---------------------------------------------------------------------------
# Individual product detectors
# ---------------------------------------------------------------------------

def detect_windows_defender() -> dict[str, Any]:
    """Native Windows Defender / Microsoft Defender Antivirus."""
    result: dict[str, Any] = {
        "provider_key": "windows_defender",
        "display_name": "Windows Defender",
    }
    if os.name != "nt":
        result.update({"installed": False, "status": "not_installed"})
        return result

    script = r"""
$ErrorActionPreference = 'SilentlyContinue'
$status = Get-MpComputerStatus
if (-not $status) { @{ installed = $false } | ConvertTo-Json -Compress; exit }
@{
  installed = $true
  version = $status.AMProductVersion
  antivirus_enabled = [bool]$status.AntivirusEnabled
  real_time_protection = [bool]$status.RealTimeProtectionEnabled
  definitions_up_to_date = -not [bool]$status.DefenderSignaturesOutOfDate
  antivirus_signature_version = $status.AntivirusSignatureVersion
  antivirus_signature_last_updated = $status.AntivirusSignatureLastUpdated
  quick_scan_end = $status.QuickScanEndTime
  full_scan_end = $status.FullScanEndTime
  is_tamper_protected = [bool]$status.IsTamperProtected
  nri_enabled = [bool]$status.NISEnabled
} | ConvertTo-Json -Compress
"""
    code, out, err = _run_ps(script)
    if code != 0 or not out:
        # Fallback: service check
        svc = _service_state("WinDefend")
        installed = svc["state"] != "not_found"
        result.update(
            {
                "installed": installed,
                "status": "healthy" if svc["state"] == "running" else ("degraded" if installed else "not_installed"),
                "real_time_protection": svc["state"] == "running",
                "details": {"service": svc, "error": err or out},
            }
        )
        return result

    try:
        data = json.loads(out)
    except Exception:
        result.update({"installed": False, "status": "unknown", "details": {"raw": out[:400]}})
        return result

    if not data.get("installed"):
        result.update({"installed": False, "status": "not_installed"})
        return result

    rtp = bool(data.get("real_time_protection"))
    defs_ok = bool(data.get("definitions_up_to_date"))
    av_on = bool(data.get("antivirus_enabled"))

    if rtp and defs_ok and av_on:
        status = "healthy"
    elif av_on:
        status = "degraded"
    else:
        status = "offline"

    last_scan = data.get("quick_scan_end") or data.get("full_scan_end")

    result.update(
        {
            "installed": True,
            "agent_version": data.get("version"),
            "status": status,
            "real_time_protection": rtp,
            "definitions_up_to_date": defs_ok,
            "last_scan_at": last_scan,
            "details": data,
        }
    )
    return result


def detect_crowdstrike() -> dict[str, Any]:
    result: dict[str, Any] = {"provider_key": "crowdstrike", "display_name": "CrowdStrike"}
    if os.name != "nt":
        result.update({"installed": False, "status": "not_installed"})
        return result

    info = _product_installed_via_uninstall(["*CrowdStrike*", "*Falcon*"])
    svc = _service_state("CSFalconService")
    installed = info.get("installed") or svc["state"] != "not_found"

    if not installed:
        result.update({"installed": False, "status": "not_installed"})
        return result

    running = svc["state"] == "running"
    result.update(
        {
            "installed": True,
            "agent_version": info.get("version"),
            "status": "healthy" if running else "degraded",
            "real_time_protection": running,
            "details": {"service": svc, "uninstall": info},
        }
    )
    return result


def detect_sentinelone() -> dict[str, Any]:
    result: dict[str, Any] = {"provider_key": "sentinelone", "display_name": "SentinelOne"}
    if os.name != "nt":
        result.update({"installed": False, "status": "not_installed"})
        return result

    info = _product_installed_via_uninstall(["*Sentinel*One*", "*SentinelAgent*"])
    # Common service names
    svc = _service_state("SentinelAgent")
    if svc["state"] == "not_found":
        svc = _service_state("SentinelStaticEngine")
    installed = info.get("installed") or svc["state"] != "not_found"

    if not installed:
        result.update({"installed": False, "status": "not_installed"})
        return result

    running = svc["state"] == "running"
    result.update(
        {
            "installed": True,
            "agent_version": info.get("version"),
            "status": "healthy" if running else "degraded",
            "real_time_protection": running,
            "details": {"service": svc, "uninstall": info},
        }
    )
    return result


def detect_huntress() -> dict[str, Any]:
    result: dict[str, Any] = {"provider_key": "huntress", "display_name": "Huntress"}
    if os.name != "nt":
        result.update({"installed": False, "status": "not_installed"})
        return result

    info = _product_installed_via_uninstall(["*Huntress*"])
    svc = _service_state("HuntressAgent")
    if svc["state"] == "not_found":
        svc = _service_state("HuntressRio")
    installed = info.get("installed") or svc["state"] != "not_found"

    if not installed:
        result.update({"installed": False, "status": "not_installed"})
        return result

    running = svc["state"] == "running"
    result.update(
        {
            "installed": True,
            "agent_version": info.get("version"),
            "status": "healthy" if running else "degraded",
            "real_time_protection": running,
            "details": {"service": svc, "uninstall": info},
        }
    )
    return result


def detect_threatlocker() -> dict[str, Any]:
    result: dict[str, Any] = {"provider_key": "threatlocker", "display_name": "ThreatLocker"}
    if os.name != "nt":
        result.update({"installed": False, "status": "not_installed"})
        return result

    info = _product_installed_via_uninstall(["*ThreatLocker*"])
    svc = _service_state("ThreatLockerSvc")
    if svc["state"] == "not_found":
        svc = _service_state("TmPfw")  # older name variants
    installed = info.get("installed") or svc["state"] != "not_found"

    if not installed:
        result.update({"installed": False, "status": "not_installed"})
        return result

    running = svc["state"] == "running"
    result.update(
        {
            "installed": True,
            "agent_version": info.get("version"),
            "status": "healthy" if running else "degraded",
            "real_time_protection": running,
            "details": {"service": svc, "uninstall": info},
        }
    )
    return result


def detect_bitdefender() -> dict[str, Any]:
    result: dict[str, Any] = {"provider_key": "bitdefender", "display_name": "Bitdefender"}
    if os.name != "nt":
        result.update({"installed": False, "status": "not_installed"})
        return result

    info = _product_installed_via_uninstall(["*Bitdefender*", "*BDAgent*"])
    svc = _service_state("bdredline")
    if svc["state"] == "not_found":
        svc = _service_state("BDRsvc")
    if svc["state"] == "not_found":
        svc = _service_state("Bitdefender Endpoint Security Service")
    installed = info.get("installed") or svc["state"] != "not_found"

    if not installed:
        result.update({"installed": False, "status": "not_installed"})
        return result

    running = svc["state"] == "running"
    result.update(
        {
            "installed": True,
            "agent_version": info.get("version"),
            "status": "healthy" if running else "degraded",
            "real_time_protection": running,
            "details": {"service": svc, "uninstall": info},
        }
    )
    return result


def detect_sophos() -> dict[str, Any]:
    result: dict[str, Any] = {"provider_key": "sophos", "display_name": "Sophos"}
    if os.name != "nt":
        result.update({"installed": False, "status": "not_installed"})
        return result

    info = _product_installed_via_uninstall(["*Sophos*"])
    svc = _service_state("Sophos Endpoint Defense Service")
    if svc["state"] == "not_found":
        svc = _service_state("SAVService")
    if svc["state"] == "not_found":
        svc = _service_state("SophosMCSAgent")
    installed = info.get("installed") or svc["state"] != "not_found"

    if not installed:
        result.update({"installed": False, "status": "not_installed"})
        return result

    running = svc["state"] == "running"
    result.update(
        {
            "installed": True,
            "agent_version": info.get("version"),
            "status": "healthy" if running else "degraded",
            "real_time_protection": running,
            "details": {"service": svc, "uninstall": info},
        }
    )
    return result


def detect_malwarebytes() -> dict[str, Any]:
    result: dict[str, Any] = {"provider_key": "malwarebytes", "display_name": "Malwarebytes"}
    if os.name != "nt":
        result.update({"installed": False, "status": "not_installed"})
        return result

    info = _product_installed_via_uninstall(["*Malwarebytes*"])
    svc = _service_state("MBAMService")
    if svc["state"] == "not_found":
        svc = _service_state("MBAMProtector")
    installed = info.get("installed") or svc["state"] != "not_found"

    if not installed:
        result.update({"installed": False, "status": "not_installed"})
        return result

    running = svc["state"] == "running"
    result.update(
        {
            "installed": True,
            "agent_version": info.get("version"),
            "status": "healthy" if running else "degraded",
            "real_time_protection": running,
            "details": {"service": svc, "uninstall": info},
        }
    )
    return result


def detect_microsoft_defender_xdr() -> dict[str, Any]:
    """Microsoft Defender for Endpoint / XDR (Sense service)."""
    result: dict[str, Any] = {
        "provider_key": "microsoft_defender_xdr",
        "display_name": "Microsoft Defender XDR",
    }
    if os.name != "nt":
        result.update({"installed": False, "status": "not_installed"})
        return result

    svc = _service_state("Sense")  # Windows Defender Advanced Threat Protection Service
    info = _product_installed_via_uninstall(["*Defender for Endpoint*", "*Microsoft Defender for Endpoint*"])
    installed = svc["state"] != "not_found" or info.get("installed")

    if not installed:
        result.update({"installed": False, "status": "not_installed"})
        return result

    running = svc["state"] == "running"
    result.update(
        {
            "installed": True,
            "agent_version": info.get("version"),
            "status": "healthy" if running else "degraded",
            "real_time_protection": running,
            "details": {"service": svc, "uninstall": info},
        }
    )
    return result


DETECTORS = [
    detect_windows_defender,
    detect_microsoft_defender_xdr,
    detect_crowdstrike,
    detect_sentinelone,
    detect_huntress,
    detect_threatlocker,
    detect_bitdefender,
    detect_sophos,
    detect_malwarebytes,
]


def scan_endpoint_security() -> dict[str, Any]:
    """Run all detectors and return a structured report."""
    hostname = socket.gethostname()
    products: list[dict[str, Any]] = []
    for detector in DETECTORS:
        try:
            products.append(detector())
        except Exception as exc:
            products.append(
                {
                    "provider_key": getattr(detector, "__name__", "unknown"),
                    "installed": False,
                    "status": "unknown",
                    "details": {"error": str(exc)},
                }
            )

    installed = [p for p in products if p.get("installed")]
    healthy = [p for p in installed if p.get("status") == "healthy"]

    return {
        "hostname": hostname,
        "platform": platform.platform(),
        "scanned_at": _utcnow(),
        "products": products,
        "summary": {
            "total_detected": len(installed),
            "healthy": len(healthy),
            "degraded": sum(1 for p in installed if p.get("status") == "degraded"),
            "offline": sum(1 for p in installed if p.get("status") == "offline"),
        },
    }


def to_ingest_payloads(scan: dict[str, Any], device_id: str | None = None) -> list[dict[str, Any]]:
    """Convert a scan report into a list of AgentIngestPayload-compatible dicts."""
    payloads = []
    for p in scan.get("products") or []:
        if not p.get("provider_key"):
            continue
        # Only report products that are installed (or explicitly not_installed for coverage)
        status = p.get("status") or ("not_installed" if not p.get("installed") else "unknown")
        payloads.append(
            {
                "provider_key": p["provider_key"],
                "device_id": device_id,
                "hostname": scan.get("hostname"),
                "agent_version": p.get("agent_version"),
                "status": status,
                "real_time_protection": p.get("real_time_protection"),
                "definitions_up_to_date": p.get("definitions_up_to_date"),
                "last_scan_at": p.get("last_scan_at"),
                "last_seen_at": scan.get("scanned_at"),
                "details": p.get("details"),
            }
        )
    return payloads
