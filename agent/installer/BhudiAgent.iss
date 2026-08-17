#define MyAppName "Bhudi Agent"
#define MyAppVersion "2.5.0"
#define MyAppPublisher "Bhudi"
#define MyAppExeName "bhudi-agent.exe"

[Setup]
AppId={{8A2B4E1C-6B3A-4A74-9E7D-BHUDIAGENT01}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Bhudi\Agent
DefaultGroupName=Bhudi Agent
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64
OutputDir=..\dist
OutputBaseFilename=BhudiAgent-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}

[Files]
Source: "..\native\dist\bhudi-agent.exe"; DestDir: "{app}"; Flags: ignoreversion

[UninstallRun]
Filename: "{app}\{#MyAppExeName}"; Parameters: "uninstall"; Flags: runhidden waituntilterminated

[Code]
var
  ServerPage: TInputQueryWizardPage;
  TokenPage: TInputQueryWizardPage;

function CmdLineValue(const Name: String): String;
var
  I: Integer;
  S, Prefix: String;
begin
  Result := '';
  Prefix := '/' + Uppercase(Name) + '=';
  for I := 1 to ParamCount do begin
    S := ParamStr(I);
    if Pos(Prefix, Uppercase(S)) = 1 then begin
      Result := Copy(S, Length(Prefix) + 1, MaxInt);
      Exit;
    end;
  end;
end;

procedure InitializeWizard;
var
  Server, Token: String;
begin
  ServerPage := CreateInputQueryPage(wpWelcome,
    'Bhudi Server', 'Connect this agent to your Bhudi server',
    'Enter the Bhudi backend URL for this customer.');
  ServerPage.Add('Server URL:', False);
  Server := CmdLineValue('SERVER');
  if Server = '' then Server := 'https://bhudi-online-production.up.railway.app';
  ServerPage.Values[0] := Server;

  TokenPage := CreateInputQueryPage(ServerPage.ID,
    'Customer Enrollment', 'Enter the customer enrollment token',
    'The token is single-use and tenant-bound and is consumed during enrollment.');
  TokenPage.Add('Enrollment token:', True);
  Token := CmdLineValue('TOKEN');
  TokenPage.Values[0] := Token;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = ServerPage.ID then begin
    if Trim(ServerPage.Values[0]) = '' then begin
      MsgBox('A server URL is required.', mbError, MB_OK);
      Result := False;
    end;
  end else if CurPageID = TokenPage.ID then begin
    if Trim(TokenPage.Values[0]) = '' then begin
      MsgBox('A customer enrollment token is required.', mbError, MB_OK);
      Result := False;
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  Exe, Params: String;
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then begin
    Exe := ExpandConstant('{app}\{#MyAppExeName}');
    Params := 'install -server "' + Trim(ServerPage.Values[0]) + '" -enrollment-token "' + Trim(TokenPage.Values[0]) + '"';
    if not Exec(Exe, Params, ExpandConstant('{app}'), SW_HIDE, ewWaitUntilTerminated, ResultCode) then
      RaiseException('Failed to start the Bhudi Agent installation step.')
    else if ResultCode <> 0 then
      RaiseException('Bhudi Agent installation failed with exit code ' + IntToStr(ResultCode) + '.');
  end;
end;
