"""Run the real Bhudi agent process against a live HTTP runtime server."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "agent" / "bhudi_agent.py"
BASE = "http://127.0.0.1:8765"
API = f"{BASE}/api/v1"


def wait_for_health() -> None:
    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            if requests.get(f"{BASE}/health", timeout=1).ok:
                return
        except requests.RequestException:
            pass
        time.sleep(0.2)
    raise AssertionError("E2E server did not become healthy")


def run_agent(identity_path: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": str(ROOT / "backend"),
            "BHUDI_SERVER_URL": BASE,
            "BHUDI_RUN_ONCE": "1",
            "BHUDI_HOSTNAME": "bhudi-ci-agent",
            "BHUDI_IDENTITY_PATH": str(identity_path),
            "BHUDI_CONFIG_PATH": str(identity_path.with_name("agent_config.json")),
            "BHUDI_ENROLL_SECRET": "e2e-test-secret",
        }
    )
    return subprocess.run(
        [sys.executable, str(AGENT)],
        cwd=ROOT / "agent",
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )


def main() -> None:
    server_env = os.environ.copy()
    server_env["PYTHONPATH"] = str(ROOT / "backend")
    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "agent.e2e_test_server:app", "--host", "127.0.0.1", "--port", "8765"],
        cwd=ROOT,
        env=server_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        wait_for_health()
        with tempfile.TemporaryDirectory(prefix="bhudi-agent-e2e-") as tmp:
            identity = Path(tmp) / "agent_identity.json"

            first = run_agent(identity)
            assert first.returncode == 0, first.stdout + first.stderr
            assert identity.exists(), "real agent did not persist enrollment identity"
            enrolled = json.loads(identity.read_text(encoding="utf-8"))
            agent_id = enrolled["agent_id"]
            agent_token = enrolled["agent_token"]

            details = requests.get(f"{API}/runtime/agents/{agent_id}", timeout=5)
            assert details.ok, details.text
            assert details.json()["status"] == "online"
            assert details.json()["hostname"] == "bhudi-ci-agent"

            command = requests.post(
                f"{API}/runtime/agents/{agent_id}/commands",
                json={"command": "printf 'BHUDI-RMM-E2E'", "shell": True},
                timeout=5,
            )
            assert command.status_code == 200, command.text
            command_id = command.json()["command_id"]

            second = run_agent(identity)
            assert second.returncode == 0, second.stdout + second.stderr

            history = requests.get(f"{API}/runtime/agents/{agent_id}/commands", timeout=5)
            assert history.ok, history.text
            commands = history.json()["commands"]
            completed = next(item for item in commands if item["command_id"] == command_id)
            assert completed["status"] == "completed"
            assert completed["exit_code"] == 0
            assert completed["stdout"] == "BHUDI-RMM-E2E"

            unauth = requests.get(
                f"{API}/runtime/agents/{agent_id}/commands/pending",
                params={"agent_token": "invalid"},
                timeout=5,
            )
            assert unauth.status_code == 401, unauth.text

            print("REAL AGENT E2E: PASS")
            print(f"agent_id={agent_id}")
            print("enrollment=PASS heartbeat=PASS command=PASS execution=PASS result=PASS auth=PASS")
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()


if __name__ == "__main__":
    main()
