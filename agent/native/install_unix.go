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

const systemdUnitName = "bhudi-agent.service"

func installService(server string) error {
	server = strings.TrimRight(server, "/")
	exe, err := os.Executable()
	if err != nil {
		return err
	}
	exe, _ = filepath.Abs(exe)

	var dest string
	if runtime.GOOS == "darwin" {
		home, _ := os.UserHomeDir()
		destDir := filepath.Join(home, "Library", "Application Support", "Bhudi", "Agent")
		_ = os.MkdirAll(destDir, 0755)
		dest = filepath.Join(destDir, "bhudi-agent")
	} else {
		// Prefer system path when root; else user local
		destDir := "/opt/bhudi/agent"
		if os.Geteuid() != 0 {
			home, _ := os.UserHomeDir()
			destDir = filepath.Join(home, ".local", "share", "bhudi", "agent")
		}
		if err := os.MkdirAll(destDir, 0755); err != nil {
			return fmt.Errorf("create install dir: %w", err)
		}
		dest = filepath.Join(destDir, "bhudi-agent")
	}

	if err := copyFile(exe, dest); err != nil {
		return fmt.Errorf("install binary: %w (try sudo)", err)
	}
	_ = os.Chmod(dest, 0755)

	if err := writeConfig(server); err != nil {
		fmt.Println("Warning: could not write config:", err)
	}

	switch runtime.GOOS {
	case "linux":
		return installSystemd(dest, server)
	case "darwin":
		return installLaunchd(dest, server)
	default:
		cmd := exec.Command(dest, "run", "-server", server)
		_ = cmd.Start()
		fmt.Println("Installed binary; started process (no service manager for this OS).")
		return nil
	}
}

func uninstallService() error {
	switch runtime.GOOS {
	case "linux":
		_ = exec.Command("systemctl", "--user", "disable", "--now", systemdUnitName).Run()
		_ = exec.Command("systemctl", "disable", "--now", systemdUnitName).Run()
		home, _ := os.UserHomeDir()
		_ = os.Remove(filepath.Join(home, ".config/systemd/user", systemdUnitName))
		_ = os.Remove(filepath.Join("/etc/systemd/system", systemdUnitName))
		_ = exec.Command("systemctl", "daemon-reload").Run()
		_ = exec.Command("systemctl", "--user", "daemon-reload").Run()
		fmt.Println("Removed systemd unit", systemdUnitName)
	case "darwin":
		plist := launchdPlistPath()
		_ = exec.Command("launchctl", "unload", plist).Run()
		_ = os.Remove(plist)
		fmt.Println("Removed LaunchAgent", plist)
	}
	fmt.Println("Uninstall complete.")
	return nil
}

func installSystemd(dest, server string) error {
	unitBody := fmt.Sprintf(`[Unit]
Description=Bhudi RMM Agent
Documentation=https://github.com/PleaseMahobo/Bhudi-Online
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=%s run -server %s
Restart=always
RestartSec=5
TimeoutStopSec=20
KillMode=process
# Allow agent to keep running across brief network drops
Environment=BHUDI_SERVER_URL=%s

[Install]
WantedBy=multi-user.target
`, dest, server, server)

	// Prefer system-wide service when root (starts at boot for all users)
	if os.Geteuid() == 0 {
		unitPath := filepath.Join("/etc/systemd/system", systemdUnitName)
		if err := os.WriteFile(unitPath, []byte(unitBody), 0644); err != nil {
			return err
		}
		_ = exec.Command("systemctl", "daemon-reload").Run()
		if out, err := exec.Command("systemctl", "enable", "--now", systemdUnitName).CombinedOutput(); err != nil {
			fmt.Println("systemctl enable failed:", strings.TrimSpace(string(out)), err)
			cmd := exec.Command(dest, "run", "-server", server)
			_ = cmd.Start()
		} else {
			fmt.Println("systemd system service enabled at boot:", unitPath)
		}
		fmt.Println("Bhudi Agent installed (native — no Python required).")
		fmt.Println("  Binary:", dest)
		fmt.Println("  Server:", server)
		fmt.Println("  Unit:  ", unitPath)
		fmt.Println("  Check:  systemctl status bhudi-agent")
		return nil
	}

	// Non-root: user unit + enable linger so it survives logout on many distros
	home, _ := os.UserHomeDir()
	userDir := filepath.Join(home, ".config/systemd/user")
	_ = os.MkdirAll(userDir, 0755)
	unitPath := filepath.Join(userDir, systemdUnitName)

	userBody := fmt.Sprintf(`[Unit]
Description=Bhudi RMM Agent (user)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=%s run -server %s
Restart=always
RestartSec=5
Environment=BHUDI_SERVER_URL=%s

[Install]
WantedBy=default.target
`, dest, server, server)

	if err := os.WriteFile(unitPath, []byte(userBody), 0644); err != nil {
		return err
	}
	_ = exec.Command("systemctl", "--user", "daemon-reload").Run()
	if out, err := exec.Command("systemctl", "--user", "enable", "--now", systemdUnitName).CombinedOutput(); err != nil {
		fmt.Println("systemctl --user enable failed:", strings.TrimSpace(string(out)))
		cmd := exec.Command(dest, "run", "-server", server)
		_ = cmd.Start()
	} else {
		fmt.Println("systemd user service enabled:", unitPath)
	}

	// Best-effort linger so user services start at boot without interactive login
	if u := os.Getenv("USER"); u != "" {
		if out, err := exec.Command("loginctl", "enable-linger", u).CombinedOutput(); err != nil {
			fmt.Println("Note: enable-linger failed (optional):", strings.TrimSpace(string(out)))
			fmt.Println("  For boot-without-login, re-run install with: sudo ./bhudi-agent install -server ...")
		} else {
			fmt.Println("linger enabled for", u, "— user service can start at boot")
		}
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

func copyFile(src, dst string) error {
	data, err := os.ReadFile(src)
	if err != nil {
		return err
	}
	return os.WriteFile(dst, data, 0755)
}
