//go:build windows

package main

import (
    "encoding/json"
    "fmt"
    "os"
    "path/filepath"
    "strings"
    "unsafe"

    "golang.org/x/sys/windows"
)

func launchDesktopWorker(serverURL, sessionID, sessionMode, displayProtocol string, monitorIndex int) error {
    sid, err := activeInteractiveSessionID()
    if err != nil { return err }
    var token windows.Token
    if err := windows.WTSQueryUserToken(sid, &token); err != nil { return fmt.Errorf("query user token for session %d: %w", sid, err) }
    defer token.Close()
    exe, err := os.Executable()
    if err != nil { return fmt.Errorf("resolve agent executable: %w", err) }
    exe, err = filepath.Abs(exe)
    if err != nil { return fmt.Errorf("resolve agent executable path: %w", err) }
    commandLine := fmt.Sprintf("\"%s\" desktop-worker -server \"%s\" -session \"%s\" -mode \"%s\" -protocol \"%s\" -monitor %d", exe, serverURL, sessionID, sessionMode, displayProtocol, monitorIndex)
    desktop, _ := windows.UTF16PtrFromString("winsta0\\default")
    cmdline, _ := windows.UTF16PtrFromString(commandLine)
    var si windows.StartupInfo
    si.Cb = uint32(unsafe.Sizeof(si))
    si.Desktop = desktop
    var pi windows.ProcessInformation
    flags := uint32(windows.CREATE_UNICODE_ENVIRONMENT | windows.CREATE_NEW_PROCESS_GROUP)
    if err := windows.CreateProcessAsUser(token, nil, cmdline, nil, nil, false, flags, nil, nil, &si, &pi); err != nil {
        return fmt.Errorf("CreateProcessAsUser desktop worker session %d: %w", sid, err)
    }
    windows.CloseHandle(pi.Thread)
    windows.CloseHandle(pi.Process)
    fmt.Printf("[remote-desktop] launched interactive worker pid=%d session=%d\n", pi.ProcessId, sid)
    return nil
}

func desktopWorkerArgs(args []string) (runConfig, string, string, string, int, bool) {
    server := envOr("BHUDI_SERVER_URL", defaultServerURL)
    sessionID, mode, protocol := "", "control", "native"
    monitor := 0
    for i := 0; i+1 < len(args); i += 2 {
        switch strings.ToLower(args[i]) {
        case "-server": server = args[i+1]
        case "-session": sessionID = args[i+1]
        case "-mode": mode = args[i+1]
        case "-protocol": protocol = args[i+1]
        case "-monitor": fmt.Sscanf(args[i+1], "%d", &monitor)
        }
    }
    if strings.TrimSpace(sessionID) == "" { return runConfig{}, "", "", "", 0, false }
    return runConfig{Server: strings.TrimRight(server, "/")}, sessionID, mode, protocol, monitor, true
}

func loadStoredIdentity() (identity, error) {
    data, err := os.ReadFile(identityPath())
    if err != nil { return identity{}, err }
    var id identity
    if err := json.Unmarshal(data, &id); err != nil { return identity{}, err }
    if strings.TrimSpace(id.AgentID) == "" || strings.TrimSpace(id.AgentToken) == "" { return identity{}, fmt.Errorf("stored agent identity is incomplete") }
    return id, nil
}
