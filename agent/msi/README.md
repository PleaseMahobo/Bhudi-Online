# Bhudi Agent MSI (enterprise)

Per-machine Windows Installer for Intune, GPO, PDQ, and SCCM.

## Properties

| Property | Default | Purpose |
|----------|---------|--------|
| `SERVERURL` | Railway production API | Backend base URL (no trailing slash) |

```bat
msiexec /i bhudi-agent-setup.msi /qn SERVERURL=https://api.example.com
```

## Build (CI)

The `release-agent` workflow builds `bhudi-agent.exe` then compiles this WiX source into `bhudi-agent-setup.msi`.

Locally (Windows + [WiX 3.14](https://wixtoolset.org/)):

```bat
cd agent\msi
candle -dAgentDir=..\native\dist Product.wxs
light -ext WixUIExtension -out bhudi-agent-setup.msi Product.wixobj
```

## Notes

- **No enrollment token** in the MSI — suitable for shared gold images; use the portal **customer EXE** for tenant-bound first install.
- Service runs as **LocalSystem**, start type **Automatic**.
- Upgrade: major upgrade removes previous version then installs; agent identity under `%ProgramData%\Bhudi\Agent` is preserved when not deleted.
