//go:build windows

package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"golang.org/x/sys/windows/registry"
)

const (
	windowsTaskName  = "BhudiAgent"
	uninstallRegPath = `SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\BhudiAgent`
	displayName      = "Bhudi Agent"
	publisherName    = "Bhudi"
)

func installService(server string) error {
	exe, err := os.Executable()
	if err != nil {
		return err
	}
	base := os.Getenv("ProgramFiles")
	if base == "" {
		base = os.Getenv("LOCALAPPDATA")
	}
	destDir := filepath.Join(base, "Bhudi", "Agent")
	if err := os.MkdirAll(destDir, 0755); err != nil {
		return err
	}
	dest := filepath.Join(destDir, "bhudi-agent.exe")
	if err := copyFile(exe, dest); err != nil {
		return err
	}

	_ = exec.Command("schtasks", "/Delete", "/TN", windowsTaskName, "/F").Run()

	cmdLine := fmt.Sprintf("\"%s\" run -server %s", dest, server)
	create := exec.Command("schtasks", "/Create", "/TN", windowsTaskName,
		"/TR", cmdLine, "/SC", "ONLOGON", "/RL", "HIGHEST", "/IT", "/F")
	out, err := create.CombinedOutput()
	if err != nil {
		return fmt.Errorf("schtasks: %v (%s)", err, strings.TrimSpace(string(out)))
	}
	_ = exec.Command("schtasks", "/Run", "/TN", windowsTaskName).Start()
	start := exec.Command(dest, "run", "-server", server)
	_ = start.Start()

	if err := writeUninstallRegistry(destDir, dest); err != nil {
		fmt.Println("Warning: could not register in Programs and Features:", err)
		fmt.Println("  (Run install as Administrator for a system-wide entry.)")
	} else {
		fmt.Println("Registered in Programs and Features as \"Bhudi Agent\".")
	}

	fmt.Println("Bhudi Agent installed (native — no Python required).")
	fmt.Println("  Binary: ", dest)
	fmt.Println("  Server: ", server)
	fmt.Println("  Task:   ", windowsTaskName)
	fmt.Println("  Mode:   interactive logon (/IT) — required for screen capture")
	time.Sleep(2 * time.Second)
	return nil
}

func writeUninstallRegistry(installDir, uninstallExe string) error {
	key, _, err := registry.CreateKey(registry.LOCAL_MACHINE, uninstallRegPath, registry.ALL_ACCESS)
	if err != nil {
		key, _, err = registry.CreateKey(registry.CURRENT_USER, uninstallRegPath, registry.ALL_ACCESS)
		if err != nil {
			return err
		}
	}
	defer key.Close()

	_ = key.SetStringValue("DisplayName", displayName)
	_ = key.SetStringValue("DisplayVersion", agentVersion)
	_ = key.SetStringValue("Publisher", publisherName)
	_ = key.SetStringValue("InstallLocation", installDir)
	_ = key.SetStringValue("UninstallString", fmt.Sprintf("\"%s\" uninstall", uninstallExe))
	_ = key.SetStringValue("DisplayIcon", uninstallExe)
	_ = key.SetDWordValue("NoModify", 1)
	_ = key.SetDWordValue("NoRepair", 1)
	_ = key.SetDWordValue("EstimatedSize", 10240)
	return nil
}

func uninstallService() error {
	_ = exec.Command("schtasks", "/Delete", "/TN", windowsTaskName, "/F").Run()
	fmt.Println("Scheduled task removed:", windowsTaskName)

	_ = registry.DeleteKey(registry.LOCAL_MACHINE, uninstallRegPath)
	_ = registry.DeleteKey(registry.CURRENT_USER, uninstallRegPath)
	fmt.Println("Removed Programs and Features entry (if present).")

	for _, base := range []string{os.Getenv("ProgramFiles"), os.Getenv("LOCALAPPDATA")} {
		if base == "" {
			continue
		}
		dest := filepath.Join(base, "Bhudi", "Agent", "bhudi-agent.exe")
		_ = os.Remove(dest)
	}
	clearIdentity()
	fmt.Println("Uninstall complete.")
	return nil
}

func copyFile(src, dst string) error {
	in, err := os.ReadFile(src)
	if err != nil {
		return err
	}
	return os.WriteFile(dst, in, 0755)
}
