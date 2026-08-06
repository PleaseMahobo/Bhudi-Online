"""
Bhudi agent — Software Deployment executor (Phase 11)

Handles package types: msi | exe | chocolatey | winget | custom
Actions: install | uninstall | rollback
Reports status transitions: downloading → installing → success | failed
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

try:
    import requests
except ImportError:
    requests = None  # type: ignore


def _platform() -> str:
    name = (sys.platform or "").lower()
    if name.startswith("win"):
        return "windows"
    if name.startswith("darwin"):
        return "macos"
    if name.startswith("linux"):
        return "linux"
    return "unknown"


def _result(
    status: str,
    *,
    exit_code: int | None = None,
    stdout: str = "",
    stderr: str = "",
    error_message: str | None = None,
    download_bytes: int | None = None,
    duration_ms: int | None = None,
    reboot_required: bool = False,
) -> dict[str, Any]:
    return {
        "status": status,
        "exit_code": exit_code,
        "stdout": (stdout or "")[:50_000],
        "stderr": (stderr or "")[:20_000],
        "error_message": error_message,
        "download_bytes": download_bytes,
        "duration_ms": duration_ms,
        "reboot_required": reboot_required,
    }


def _run(
    cmd: list[str] | str,
    *,
    shell: bool = False,
    timeout: int = 3600,
    cwd: str | None = None,
) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            cmd,
            shell=shell,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
        return {
            "exit_code": completed.returncode,
            "stdout": completed.stdout or "",
            "stderr": completed.stderr or "",
        }
    except subprocess.TimeoutExpired:
        return {"exit_code": 124, "stdout": "", "stderr": "command timed out"}
    except FileNotFoundError as e:
        return {"exit_code": 127, "stdout": "", "stderr": str(e)}
    except Exception as e:
        return {"exit_code": 1, "stdout": "", "stderr": str(e)}


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _download(url: str, dest: Path, expected_sha256: str | None = None) -> tuple[int, str | None]:
    """Download to dest. Returns (bytes_written, error)."""
    if requests is None:
        return 0, "requests library not installed"
    try:
        with requests.get(url, stream=True, timeout=120) as r:
            r.raise_for_status()
            dest.parent.mkdir(parents=True, exist_ok=True)
            written = 0
            with dest.open("wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 256):
                    if chunk:
                        f.write(chunk)
                        written += len(chunk)
        if expected_sha256:
            actual = _sha256_file(dest)
            if actual.lower() != expected_sha256.lower():
                dest.unlink(missing_ok=True)
                return written, f"sha256 mismatch: expected {expected_sha256}, got {actual}"
        return written, None
    except Exception as e:
        return 0, str(e)


def _success_codes(pkg: dict[str, Any]) -> set[int]:
    codes = pkg.get("success_exit_codes") or [0]
    return {int(c) for c in codes}


def _is_success(exit_code: int, pkg: dict[str, Any]) -> bool:
    return exit_code in _success_codes(pkg)


def _install_msi(path: Path, pkg: dict[str, Any], timeout: int) -> dict[str, Any]:
    args = (pkg.get("install_args") or "/qn /norestart").strip()
    # msiexec /i package.msi ARGS
    cmd = f'msiexec /i "{path}" {args}'
    return _run(cmd, shell=True, timeout=timeout)


def _uninstall_msi(path: Path | None, pkg: dict[str, Any], timeout: int) -> dict[str, Any]:
    if pkg.get("uninstall_command"):
        return _run(pkg["uninstall_command"], shell=True, timeout=timeout)
    args = (pkg.get("uninstall_args") or "/qn /norestart").strip()
    if path and path.exists():
        cmd = f'msiexec /x "{path}" {args}'
        return _run(cmd, shell=True, timeout=timeout)
    # Product code style uninstall needs uninstall_command from package
    return {
        "exit_code": 1,
        "stdout": "",
        "stderr": "MSI uninstall requires uninstall_command or local package path",
    }


def _install_exe(path: Path, pkg: dict[str, Any], timeout: int) -> dict[str, Any]:
    args = (pkg.get("install_args") or "/S").strip()
    cmd = f'"{path}" {args}'.strip()
    return _run(cmd, shell=True, timeout=timeout)


def _uninstall_exe(pkg: dict[str, Any], timeout: int) -> dict[str, Any]:
    if pkg.get("uninstall_command"):
        return _run(pkg["uninstall_command"], shell=True, timeout=timeout)
    args = (pkg.get("uninstall_args") or "").strip()
    if not args and not pkg.get("uninstall_command"):
        return {
            "exit_code": 1,
            "stdout": "",
            "stderr": "EXE uninstall requires uninstall_command",
        }
    return _run(args, shell=True, timeout=timeout)


def _choco_install(pkg: dict[str, Any], timeout: int) -> dict[str, Any]:
    choco = shutil.which("choco")
    if not choco:
        return {"exit_code": 127, "stdout": "", "stderr": "Chocolatey (choco) not found on PATH"}
    pkg_id = pkg.get("choco_id") or pkg.get("name")
    version = pkg.get("version")
    args = (pkg.get("install_args") or "-y").strip()
    cmd = [choco, "install", str(pkg_id), args]
    if version and version != "1.0.0":
        cmd = [choco, "install", str(pkg_id), "--version", str(version), args]
    # join extra args as shell for choco flexibility
    return _run(" ".join(str(c) for c in cmd if c), shell=True, timeout=timeout)


def _choco_uninstall(pkg: dict[str, Any], timeout: int) -> dict[str, Any]:
    choco = shutil.which("choco")
    if not choco:
        return {"exit_code": 127, "stdout": "", "stderr": "Chocolatey (choco) not found on PATH"}
    pkg_id = pkg.get("choco_id") or pkg.get("name")
    args = (pkg.get("uninstall_args") or "-y").strip()
    return _run(f'{choco} uninstall {pkg_id} {args}', shell=True, timeout=timeout)


def _winget_install(pkg: dict[str, Any], timeout: int) -> dict[str, Any]:
    winget = shutil.which("winget")
    if not winget:
        return {"exit_code": 127, "stdout": "", "stderr": "winget not found on PATH"}
    pkg_id = pkg.get("winget_id") or pkg.get("name")
    args = (pkg.get("install_args") or "--accept-package-agreements --accept-source-agreements --silent").strip()
    version = pkg.get("version")
    cmd = f'"{winget}" install --id "{pkg_id}" {args}'
    if version and version not in ("1.0.0", "latest"):
        cmd += f' --version "{version}"'
    return _run(cmd, shell=True, timeout=timeout)


def _winget_uninstall(pkg: dict[str, Any], timeout: int) -> dict[str, Any]:
    winget = shutil.which("winget")
    if not winget:
        return {"exit_code": 127, "stdout": "", "stderr": "winget not found on PATH"}
    pkg_id = pkg.get("winget_id") or pkg.get("name")
    args = (pkg.get("uninstall_args") or "--silent").strip()
    return _run(f'"{winget}" uninstall --id "{pkg_id}" {args}', shell=True, timeout=timeout)


def _custom_install(pkg: dict[str, Any], path: Path | None, timeout: int) -> dict[str, Any]:
    args = (pkg.get("install_args") or "").strip()
    if not args and path:
        args = f'"{path}"'
    if not args:
        return {"exit_code": 1, "stdout": "", "stderr": "custom package requires install_args"}
    return _run(args, shell=True, timeout=timeout)


def _custom_uninstall(pkg: dict[str, Any], timeout: int) -> dict[str, Any]:
    cmd = (pkg.get("uninstall_command") or pkg.get("uninstall_args") or "").strip()
    if not cmd:
        return {"exit_code": 1, "stdout": "", "stderr": "custom package requires uninstall_command"}
    return _run(cmd, shell=True, timeout=timeout)


def execute_deployment(
    payload: dict[str, Any],
    *,
    report: Callable[[dict[str, Any]], None] | None = None,
    work_dir: Path | None = None,
) -> dict[str, Any]:
    """
    Execute a deployment from agent_payload() response shape:

      {
        "job_id": "...",
        "target_id": "...",
        "action": "install" | "uninstall" | "rollback",
        "package": { ... }
      }
    """
    t0 = time.monotonic()
    action = str(payload.get("action") or "install").lower()
    pkg = payload.get("package") or {}
    package_type = str(pkg.get("package_type") or "").lower()
    timeout = int(pkg.get("timeout_seconds") or 3600)
    requires_reboot = bool(pkg.get("requires_reboot"))
    download_bytes = 0
    local_path: Path | None = None
    tmp_root: Path | None = None

    def _report(status: str, **kwargs: Any) -> None:
        if report:
            report(_result(status, **kwargs))

    # Platform gate for Windows-centric package managers
    if package_type in ("msi", "chocolatey", "winget") and _platform() != "windows":
        return _result(
            "failed",
            exit_code=1,
            error_message=f"{package_type} packages require Windows",
            duration_ms=int((time.monotonic() - t0) * 1000),
        )

    try:
        # Download when source_url present (msi/exe/custom)
        needs_file = package_type in ("msi", "exe", "custom") and bool(pkg.get("source_url"))
        if needs_file and action == "install":
            _report("downloading")
            tmp_root = Path(work_dir or tempfile.mkdtemp(prefix="bhudi-deploy-"))
            fname = pkg.get("file_name") or Path(pkg["source_url"]).name or "package.bin"
            local_path = tmp_root / fname
            written, err = _download(pkg["source_url"], local_path, pkg.get("sha256"))
            download_bytes = written
            if err:
                return _result(
                    "failed",
                    exit_code=1,
                    error_message=err,
                    download_bytes=download_bytes,
                    duration_ms=int((time.monotonic() - t0) * 1000),
                )

        _report("installing" if action == "install" else "installing", download_bytes=download_bytes)

        is_remove = action in ("uninstall", "rollback")

        if package_type == "msi":
            raw = (
                _uninstall_msi(local_path, pkg, timeout)
                if is_remove
                else _install_msi(local_path, pkg, timeout)  # type: ignore[arg-type]
            )
        elif package_type == "exe":
            raw = _uninstall_exe(pkg, timeout) if is_remove else _install_exe(local_path, pkg, timeout)  # type: ignore[arg-type]
        elif package_type == "chocolatey":
            raw = _choco_uninstall(pkg, timeout) if is_remove else _choco_install(pkg, timeout)
        elif package_type == "winget":
            raw = _winget_uninstall(pkg, timeout) if is_remove else _winget_install(pkg, timeout)
        elif package_type == "custom":
            raw = (
                _custom_uninstall(pkg, timeout)
                if is_remove
                else _custom_install(pkg, local_path, timeout)
            )
        else:
            return _result(
                "failed",
                exit_code=1,
                error_message=f"unsupported package_type: {package_type}",
                duration_ms=int((time.monotonic() - t0) * 1000),
            )

        exit_code = int(raw.get("exit_code", 1))
        ok = _is_success(exit_code, pkg)
        final_status = "rolled_back" if (is_remove and ok) else ("success" if ok else "failed")

        return _result(
            final_status,
            exit_code=exit_code,
            stdout=raw.get("stdout", ""),
            stderr=raw.get("stderr", ""),
            error_message=None if ok else (raw.get("stderr") or f"exit_code={exit_code}"),
            download_bytes=download_bytes or None,
            duration_ms=int((time.monotonic() - t0) * 1000),
            reboot_required=requires_reboot and ok and action == "install",
        )
    except Exception as e:
        return _result(
            "failed",
            exit_code=1,
            error_message=str(e),
            download_bytes=download_bytes or None,
            duration_ms=int((time.monotonic() - t0) * 1000),
        )
    finally:
        if tmp_root and tmp_root.exists():
            try:
                shutil.rmtree(tmp_root, ignore_errors=True)
            except Exception:
                pass
