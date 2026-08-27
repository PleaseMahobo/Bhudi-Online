package main

import (
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"time"
)

func installLogPath() string {
	switch runtime.GOOS {
	case "windows":
		base := os.Getenv("ProgramData")
		if base == "" {
			base = os.Getenv("LOCALAPPDATA")
		}
		return filepath.Join(base, "Bhudi", "Agent", "install.log")
	case "darwin":
		home, _ := os.UserHomeDir()
		return filepath.Join(home, "Library", "Logs", "Bhudi", "install.log")
	default:
		if os.Geteuid() == 0 {
			return "/var/log/bhudi-agent-install.log"
		}
		home, _ := os.UserHomeDir()
		return filepath.Join(home, ".local", "share", "bhudi-agent", "install.log")
	}
}

func logInstall(format string, args ...any) {
	msg := fmt.Sprintf(format, args...)
	line := fmt.Sprintf("%s %s\n", time.Now().UTC().Format(time.RFC3339), msg)
	fmt.Print(line)
	path := installLogPath()
	_ = os.MkdirAll(filepath.Dir(path), 0755)
	f, err := os.OpenFile(path, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0644)
	if err != nil {
		return
	}
	defer f.Close()
	_, _ = f.WriteString(line)
}
