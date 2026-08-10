//go:build windows

package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"syscall"
	"time"

	"golang.org/x/sys/windows/registry"
)

const (
	windowsTaskName     = "BhudiAgent"
	windowsWatchdogName = "BhudiAgentWatchdog"
	uninstallRegPath    = `SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\BhudiAgent`
	displayName         = "Bhudi Agent"
	publisherName       = "Bhudi"
	runKeyPath          = `Software\Microsoft\Windows\CurrentVersion\Run`
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
		"/TR", cmdLine, "/SC", "ONLOGON", "/RL", "HIGHEST", "/IT", "/F")
	if out, err := create.CombinedOutput(); err != nil {
		fmt.Printf("Warning: logon task failed: %v (%s)\n", err, strings.TrimSpace(string(out)))
	} else {
		fmt.Println("Logon task:", windowsTaskName)
	}

	_ = exec.Command("schtasks", "/Delete", "/TN", windowsWatchdogName, "/F").Run()
	watch := exec.Command("schtasks", "/Create", "/TN", windowsWatchdogName,
		"/TR", cmdLine, "/SC", "MINUTE", "/MO", "5", "/RL", "HIGHEST", "/IT", "/F")
	if out, err := watch.CombinedOutput(); err != nil {
		fmt.Printf("Warning: watchdog task failed: %v (%s)\n", err, strings.TrimSpace(string(out)))
	} else {
		fmt.Println("Watchdog task:", windowsWatchdogName, "(every 5 minutes)")
	}

	if err := writeRunKey(dest, server); err != nil {
		fmt.Println("Warning: Run key not set:", err)
	} else {
		fmt.Println("Startup Run key registered.")
	}

	if err := writeUninstallRegistry(destDir, dest); err != nil {
		fmt.Println("Warning: Programs and Features entry failed:", err)
	} else {
		fmt.Println("Registered in Apps & features as \"Bhudi Agent\".")
	}

	if err := startDetached(dest, server); err != nil {
		fmt.Println("Warning: could not start agent now:", err)
	} else {
		fmt.Println("Agent started in the background (stays up after this window closes).")
	}

	fmt.Println()
	fmt.Println("Install complete — install once; the agent keeps reconnecting.")
	fmt.Println("  Binary:   ", dest)
	fmt.Println("  Server:   ", server)
	fmt.Println("  Identity: ", identityPath())
	fmt.Println()
	fmt.Println("Persistence: logon start + 5-minute watchdog + same PC identity")
	time.Sleep(1 * time.Second)
	return nil
}

func startDetached(dest, server string) error {
	cmd := exec.Command(dest, "run", "-server", server)
	cmd.Stdout = nil
	cmd.Stderr = nil
	cmd.Stdin = nil
	cmd.SysProcAttr = &syscall.SysProcAttr{
		CreationFlags: 0x00000008 | 0x00000200,
		HideWindow:    true,
	}
	return cmd.Start()
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
	_ = exec.Command("schtasks", "/Delete", "/TN", windowsWatchdogName, "/F").Run()
	fmt.Println("Scheduled tasks removed.")
	if key, err := registry.OpenKey(registry.CURRENT_USER, runKeyPath, registry.SET_VALUE); err == nil {
		_ = key.DeleteValue("BhudiAgent")
		key.Close()
	}
	_ = registry.DeleteKey(registry.LOCAL_MACHINE, uninstallRegPath)
	_ = registry.DeleteKey(registry.CURRENT_USER, uninstallRegPath)
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
