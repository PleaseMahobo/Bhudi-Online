//go:build windows

package main

import (
    "fmt"
    "os"
    "os/exec"
)

func ensureElevated() {
    if os.Getenv("BHUDI_SETUP_ELEVATED") == "1" {
        return
    }
    if err := exec.Command("net", "session").Run(); err == nil {
        return
    }
    exe, err := os.Executable()
    if err != nil {
        fmt.Fprintln(os.Stderr, fmt.Errorf("unable to determine installer path: %w", err))
        os.Exit(1)
    }
    script := "$p=Start-Process -FilePath $env:BHUDI_SETUP_EXE -Verb RunAs -PassThru -Wait; exit $p.ExitCode"
    cmd := exec.Command("powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script)
    cmd.Env = append(os.Environ(), "BHUDI_SETUP_ELEVATED=1", "BHUDI_SETUP_EXE="+exe)
    cmd.Stdout, cmd.Stderr, cmd.Stdin = os.Stdout, os.Stderr, os.Stdin
    if err := cmd.Run(); err != nil {
        fmt.Fprintln(os.Stderr, fmt.Errorf("administrator elevation failed: %w", err))
        os.Exit(1)
    }
    os.Exit(0)
}
