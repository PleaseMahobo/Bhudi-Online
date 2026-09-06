# Remaining gaps (full RMM parity)

## 1. Patch compliance from live agent scans — **improved**

**API:** `GET /api/v1/patch-management/compliance`

Now includes `live_agent_compliance` built from the **latest successful `patch_scan`** command per agent:

- `devices_scanned`, `compliant`, `noncompliant`, `compliance_pct`
- Per-device: hostname, missing update count, critical/important count, scanned_at

**Flow:** rollout execute `action=scan` → agents run Windows Update COM → results stored on `agent_commands` → compliance endpoint aggregates them.

Still optional later: dedicated `patch_snapshots` table, scheduled scans, portal charts.

---

## 2. Remote desktop / terminal — hooks only

**Agent (present):**

- `remote.terminal.start`
- `remote.desktop.start`
- `remote.desktop.webrtc`
- Screen capture modules on Windows

**Still needed for product polish:**

- Portal viewer (reconnect, multi-monitor)
- Reliable input path (keyboard/mouse)
- Consent / audit UI
- TURN/STUN for WebRTC NAT traversal

Until then: use remote **scripts/commands** and Support tickets for day-to-day ops.

---

## 3. Code signing (SmartScreen)

Unsigned EXEs may show “Windows protected your PC”.

**To sign builds in CI** (already wired as optional in `release-agent.yml`):

1. Obtain an Authenticode certificate (EV preferred for reputation).
2. Add GitHub secrets:
   - `WINDOWS_SIGN_CERT_BASE64` — PFX as base64
   - `WINDOWS_SIGN_CERT_PASSWORD`
3. Re-run **Release Native Agent** / build workflow.

Until then: users choose **More info → Run anyway** on SmartScreen, or deploy via MSI + Intune (often quieter for managed fleets).
