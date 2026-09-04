# Bhudi Agent MSI (enterprise)

Per-machine Windows Installer for Intune, GPO, PDQ, and SCCM.

**Toolchain:** WiX Toolset **5** only (matches `Product.wxs`). Do not use candle/light (v3).

## Properties

| Property | Default | Purpose |
|----------|---------|--------|
| `SERVERURL` | Railway production API | Backend base URL (no trailing slash) |
| `ENROLLMENTTOKEN` | *(empty)* | Optional multi-use enrollment token written to `%ProgramData%\Bhudi\Agent\enrollment_token.txt` for first bind |

```bat
msiexec /i bhudi-agent-setup.msi /qn SERVERURL=https://bhudi-online-production.up.railway.app ENROLLMENTTOKEN=your-token-here
```

## Customer tokens vs MSI

| Path | Token injection |
|------|-----------------|
| **Portal `BhudiAgent-Setup.exe`** | Automatic (bootstrap trailer) — use for end-user downloads |
| **This MSI** | Manual / MDM property `ENROLLMENTTOKEN` — use for mass deploy |

## Build (CI)

`build-agent-setup.yml` builds `bhudi-agent.exe` + `bhudi-support.exe`, then:

```bat
wix build Product.wxs -ext WixToolset.UI.wixext -d AgentDir=. -o bhudi-agent-setup.msi
```

Both binaries must be present in `AgentDir`.

Locally (Windows + [WiX 5](https://wixtoolset.org/)):

```bat
dotnet tool install --global wix --version 5.0.2
wix extension add -g WixToolset.UI.wixext/5.0.2
cd agent\msi
copy ..\native\dist\bhudi-agent.exe .
copy ..\native\dist\bhudi-support.exe .
wix build Product.wxs -ext WixToolset.UI.wixext -d AgentDir=. -o bhudi-agent-setup.msi
```

## Notes

- Service runs as **LocalSystem**, start type **Automatic**.
- Packages **agent + Support Client** (tray ticketing).
- Upgrade: major upgrade removes previous version then installs; agent identity under `%ProgramData%\Bhudi\Agent` is preserved when not deleted.
