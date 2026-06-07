[Setup]
AppName=BHUDI Agent
AppVersion=1.0
DefaultDirName={pf}\BHUDI Agent
DefaultGroupName=BHUDI Agent
OutputDir=output
OutputBaseFilename=bhudi-agent-installer

[Files]
Source: "dist\agent.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\BHUDI Agent"; Filename: "{app}\agent.exe"

[Run]
Filename: "{app}\agent.exe"; Description: "Launch BHUDI Agent"; Flags: nowait postinstall skipifsilent