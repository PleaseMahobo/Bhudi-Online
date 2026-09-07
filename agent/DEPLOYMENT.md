# Bhudi Agent 2.2.8 — Silent install & deployment tools

## Silent EXE

```bat
bhudi-agent.exe upgrade -server https://YOUR-API
bhudi-agent.exe install -server https://YOUR-API
bhudi-agent.exe version
```

## Silent MSI

```bat
msiexec /i bhudi-agent-setup.msi /qn /norestart SERVERURL=https://YOUR-API
```

## Exit codes (SILENT_*.bat kit)

| Code | Meaning |
|------|--------|
| 0 | Success |
| 1 | Agent install/upgrade failed |
| 2 | bhudi-agent.exe missing from package |
| 3 | bhudi-support.exe missing |

## Intune / GPO / PDQ

- Install: `SILENT_UPGRADE.bat https://YOUR-API` or MSI command above
- Detection: service `BhudiAgent` + `bhudi-agent.exe version` contains `2.2.8`
- Context: System
- Ship `bhudi-support.exe` beside the agent for tray tickets

## GitHub release

Tag: `agent-native-latest`  
https://github.com/PleaseMahobo/Bhudi-Online/releases/tag/agent-native-latest
