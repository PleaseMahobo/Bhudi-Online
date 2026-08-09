//go:build !windows

package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
)

func installService(server string) error {
	exe, err := os.Executable()
	if err != nil {
		return err
	}
	exe, _ = filepath.Abs(exe)

	destDir := "/usr/local/bin"
	if err := os.MkdirAll(destDir, 0755); err != nil {
		home, _ := os.UserHomeDir()
		destDir = filepath.Join(home, ".local", "bin")
		_ = os.MkdirAll(destDir, 0755)
	}
	dest := filepath.Join(destDir, "bhudi-agent")
	data, err := os.ReadFile(exe)
	if err != nil {
		return err
	}
	if err := os.WriteFile(dest, data, 0755); err != nil {
		return fmt.Errorf("install binary: %w (try sudo)", err)
	}
	_ = writeConfig(server)

	if runtime.GOOS == "darwin" {
		return installLaunchd(dest, server)
	}
	return installSystemd(dest, server)
}

func uninstallService() error {
	if runtime.GOOS == "darwin" {
		plist := launchdPlistPath()
		_ = exec.Command("launchctl", "unload", plist).Run()
		_ = os.Remove(plist)
		fmt.Println("Removed LaunchAgent")
		return nil
	}
	unit := "bhudi-agent.service"
	_ = exec.Command("systemctl", "--user", "disable", "--now", unit).Run()
	_ = exec.Command("systemctl", "disable", "--now", unit).Run()
	home, _ := os.UserHomeDir()
	_ = os.Remove(filepath.Join(home, ".config/systemd/user", unit))
	_ = os.Remove(filepath.Join("/etc/systemd/system", unit))
	fmt.Println("Removed systemd unit")
	return nil
}

func installSystemd(dest, server string) error {
	home, _ := os.UserHomeDir()
	userDir := filepath.Join(home, ".config/systemd/user")
	_ = os.MkdirAll(userDir, 0755)
	unitPath := filepath.Join(userDir, "bhudi-agent.service")
	content := fmt.Sprintf(`[Unit]
Description=Bhudi RMM Agent
After=network-online.target

[Service]
Type=simple
ExecStart=%s run -server %s
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
`, dest, server)
	if err := os.WriteFile(unitPath, []byte(content), 0644); err != nil {
		return err
	}
	_ = exec.Command("systemctl", "--user", "daemon-reload").Run()
	if out, err := exec.Command("systemctl", "--user", "enable", "--now", "bhudi-agent.service").CombinedOutput(); err != nil {
		fmt.Println("systemctl user enable failed:", strings.TrimSpace(string(out)))
		cmd := exec.Command(dest, "run", "-server", server)
		_ = cmd.Start()
	}
	fmt.Println("Bhudi Agent installed (native — no Python required).")
	fmt.Println("  Binary:", dest)
	fmt.Println("  Server:", server)
	fmt.Println("  Unit:  ", unitPath)
	return nil
}

func launchdPlistPath() string {
	home, _ := os.UserHomeDir()
	return filepath.Join(home, "Library/LaunchAgents/com.bhudi.agent.plist")
}

func installLaunchd(dest, server string) error {
	plist := launchdPlistPath()
	_ = os.MkdirAll(filepath.Dir(plist), 0755)
	content := fmt.Sprintf(`<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.bhudi.agent</string>
  <key>ProgramArguments</key>
  <array>
    <string>%s</string>
    <string>run</string>
    <string>-server</string>
    <string>%s</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
</dict>
</plist>
`, dest, server)
	if err := os.WriteFile(plist, []byte(content), 0644); err != nil {
		return err
	}
	_ = exec.Command("launchctl", "unload", plist).Run()
	if out, err := exec.Command("launchctl", "load", plist).CombinedOutput(); err != nil {
		fmt.Println("launchctl load:", strings.TrimSpace(string(out)), err)
		cmd := exec.Command(dest, "run", "-server", server)
		_ = cmd.Start()
	}
	fmt.Println("Bhudi Agent installed (native — no Python required).")
	fmt.Println("  Binary:", dest)
	fmt.Println("  Server:", server)
	fmt.Println("  Plist: ", plist)
	return nil
}
