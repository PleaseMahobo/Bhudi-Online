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
	uninstallRegPath = `SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\BhudiAgent`
	displayName      = "Bhudi Agent"
	publisherName    = "Bhudi"
	runKeyPath       = `Software\Microsoft\Windows\CurrentVersion\Run`
)

func installService(server string) error {
	server = strings.TrimRight(server, "/")
	exe, err := os.Executable()
	if err != nil {
		return err
	}
	exe, _ = filepath.Abs(exe)

	destDir := filepath.Join(os.Getenv("ProgramFiles"), "Bhudi", "Agent")
	if err := os.MkdirAll(destDir, 0755); err != nil {
		destDir = filepath.Join(os.Getenv("LOCALAPPDATA"), "Bhudi", "Agent")
		if err := os.MkdirAll(destDir, 0755); err != nil {
			return fmt.Errorf("create install dir: %w", err)
		}
	}
	dest := filepath.Join(destDir, "bhudi-agent.exe")
	if err := copyFile(exe, dest); err != nil {
		return fmt.Errorf("copy agent: %w", err)
	}

	if err := writeConfig(server); err != nil {
		fmt.Println("Warning: could not write config:", err)
	}

	cmdLine := fmt.Sprintf("\"%s\" run -server %s", dest, server)

	_ = exec.Command("schtasks", "/Delete", "/TN", windowsTaskName, "/F").Run()
	create := exec.Command("schtasks", "/Create", "/TN", windowsTaskName,
		"/TR", cmdLine,
		"/SC", "ONLOGON",
		"/RL", "HIGHEST",
		"/IT",
		"/F",
	)
	out, err := create.CombinedOutput()
	if err != nil {
		fmt.Printf("Warning: scheduled task failed: %v (%s)\n", err, strings.TrimSpace(string(out)))
		fmt.Println("  Falling back to Startup Run key only.")
	} else {
		fmt.Println("Scheduled task created:", windowsTaskName, "(starts at every logon)")
		_ = exec.Command("schtasks", "/Run", "/TN", windowsTaskName).Start()
	}

	if err := writeRunKey(dest, server); err != nil {
		fmt.Println("Warning: Run key not set:", err)
	} else {
		fmt.Println("Startup Run key registered (HKCU).")
	}

	if err := writeUninstallRegistry(destDir, dest); err != nil {
		fmt.Println("Warning: Programs and Features entry failed:", err)
		fmt.Println("  Run install as Administrator for a system-wide entry.")
	} else {
		fmt.Println("Registered in Apps & features as \"Bhudi Agent\".")
	}

	start := exec.Command(dest, "run", "-server", server)
	if err := start.Start(); err != nil {
		fmt.Println("Warning: could not start agent now:", err)
	} else {
		fmt.Println("Agent started in the background.")
	}

	fmt.Println()
	fmt.Println("Install complete — you only need to do this once on this PC.")
	fmt.Println("  Binary:  ", dest)
	fmt.Println("  Server:  ", server)
	fmt.Println("  Identity:", identityPath())
	fmt.Println("  Config:  ", filepath.Join(dataDir(), "agent_config.json"))
	fmt.Println()
	fmt.Println("After reboot / re-login the agent starts automatically.")
	fmt.Println("Screen share requires a logged-in desktop session.")
	time.Sleep(2 * time.Second)
	return nil
}

func writeRunKey(dest, server string) error {
	key, _, err := registry.CreateKey(registry.CURRENT_USER, runKeyPath, registry.SET_VALUE)
	if err != nil {
		return err
	}
	defer key.Close()
	val := fmt.Sprintf("\"%s\" run -server %s", dest, server)
	return key.SetStringValue("BhudiAgent", val)
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

	if key, err := registry.OpenKey(registry.CURRENT_USER, runKeyPath, registry.SET_VALUE); err == nil {
		_ = key.DeleteValue("BhudiAgent")
		key.Close()
	}

	_ = registry.DeleteKey(registry.LOCAL_MACHINE, uninstallRegPath)
	_ = registry.DeleteKey(registry.CURRENT_USER, uninstallRegPath)
	fmt.Println("Removed Programs and Features / Run key entries.")

	for _, base := range []string{os.Getenv("ProgramFiles"), os.Getenv("LOCALAPPDATA")} {
		if base == "" {
			continue
		}
		_ = os.Remove(filepath.Join(base, "Bhudi", "Agent", "bhudi-agent.exe"))
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
