//go:build windows

package main

import (
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"syscall"
	"time"

	"golang.org/x/sys/windows/registry"
)

const (
	windowsServiceName  = "BhudiAgent"
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
	logInstall("install: dest=%s", dest)
	if err := copyFile(exe, dest); err != nil {
		return fmt.Errorf("copy agent: %w", err)
	}

	if err := writeConfig(server); err != nil {
		fmt.Println("Warning: could not write config:", err)
	}

	if err := installWindowsService(dest, server); err != nil {
		fmt.Printf("Warning: Windows Service install failed: %v\n", err)
		fmt.Println("Falling back to ONSTART scheduled task...")
		if err2 := installOnStartTask(dest, server); err2 != nil {
			fmt.Printf("Warning: ONSTART task failed: %v\n", err2)
		}
	} else {
		fmt.Println("Windows Service installed:", windowsServiceName, "(Start=Automatic)")
	}

	// The watchdog is intentionally a foreground agent invocation. It is a
	// recovery path, not the SCM service entrypoint.
	cmdLine := fmt.Sprintf("\"%s\" run -server %s", dest, server)
	_ = exec.Command("schtasks", "/Delete", "/TN", windowsWatchdogName, "/F").Run()
	watch := exec.Command("schtasks", "/Create", "/TN", windowsWatchdogName,
		"/TR", cmdLine, "/SC", "MINUTE", "/MO", "5", "/RL", "HIGHEST", "/F")
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
		fmt.Println("Registered in Apps & features as", displayName)
	}

	if err := startWindowsService(); err != nil {
		return fmt.Errorf("start Windows service: %w", err)
	}

	fmt.Println("Service started.")
	fmt.Println()
	fmt.Println("Install complete — install once; agent starts at every boot.")
	fmt.Println("  Binary:   ", dest)
	fmt.Println("  Server:   ", server)
	fmt.Println("  Identity: ", identityPath())
	fmt.Println("  Service:  ", windowsServiceName, "(Automatic)")
	time.Sleep(1 * time.Second)
	return nil
}

func upgradeService(server string) error {
	server = strings.TrimRight(server, "/")
	if server == "" {
		server = defaultServerURL
	}
	logInstall("upgrade: stopping service")
	_ = exec.Command("sc", "stop", windowsServiceName).Run()
	time.Sleep(800 * time.Millisecond)
	return installService(server)
}

func installWindowsService(dest, server string) error {
	_ = exec.Command("sc", "stop", windowsServiceName).Run()
	_ = exec.Command("sc", "delete", windowsServiceName).Run()
	time.Sleep(500 * time.Millisecond)

	// Windows Service Control Manager requires the executable to enter the
	// service dispatcher. The previous "run" entrypoint bypassed SCM and caused
	// StartService error 1053. Use the native service entrypoint instead.
	binPath := fmt.Sprintf("\"%s\" service -server %s", dest, server)
	create := exec.Command("sc", "create", windowsServiceName,
		"binPath=", binPath,
		"start=", "auto",
		"DisplayName=", displayName,
		"obj=", "LocalSystem",
	)
	out, err := create.CombinedOutput()
	if err != nil {
		return fmt.Errorf("%v: %s", err, strings.TrimSpace(string(out)))
	}

	_ = exec.Command("sc", "description", windowsServiceName,
		"Bhudi RMM agent — heartbeats, remote access, command execution").Run()
	_ = exec.Command("sc", "failure", windowsServiceName,
		"reset=", "86400",
		"actions=", "restart/5000/restart/10000/restart/30000").Run()
	_ = exec.Command("sc", "failureflag", windowsServiceName, "1").Run()
	_ = exec.Command("sc", "config", windowsServiceName, "start=", "delayed-auto").Run()
	return nil
}

func startWindowsService() error {
	out, err := exec.Command("sc", "start", windowsServiceName).CombinedOutput()
	if err != nil {
		msg := strings.TrimSpace(string(out))
		if strings.Contains(msg, "1056") || strings.Contains(strings.ToLower(msg), "already") {
			return nil
		}
		return fmt.Errorf("%v: %s", err, msg)
	}
	return nil
}

func installOnStartTask(dest, server string) error {
	cmdLine := fmt.Sprintf("\"%s\" run -server %s", dest, server)
	_ = exec.Command("schtasks", "/Delete", "/TN", windowsTaskName, "/F").Run()
	create := exec.Command("schtasks", "/Create", "/TN", windowsTaskName,
		"/TR", cmdLine, "/SC", "ONSTART", "/RU", "SYSTEM", "/RL", "HIGHEST", "/F")
	out, err := create.CombinedOutput()
	if err != nil {
		return fmt.Errorf("%v: %s", err, strings.TrimSpace(string(out)))
	}
	fmt.Println("Boot task (ONSTART):", windowsTaskName)
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
	logInstall("uninstall: stopping service %s", windowsServiceName)
	_ = exec.Command("sc", "stop", windowsServiceName).Run()
	_ = exec.Command("sc", "delete", windowsServiceName).Run()
	fmt.Println("Windows Service removed:", windowsServiceName)

	_ = exec.Command("schtasks", "/Delete", "/TN", windowsTaskName, "/F").Run()
	_ = exec.Command("schtasks", "/Delete", "/TN", windowsWatchdogName, "/F").Run()
	fmt.Println("Scheduled tasks removed.")

	if key, err := registry.OpenKey(registry.CURRENT_USER, runKeyPath, registry.SET_VALUE); err == nil {
		_ = key.DeleteValue("BhudiAgent")
		key.Close()
	}
	_ = registry.DeleteKey(registry.LOCAL_MACHINE, uninstallRegPath)
	_ = registry.DeleteKey(registry.CURRENT_USER, uninstallRegPath)
	fmt.Println("Startup and uninstall registry cleaned.")
	fmt.Println("Uninstall complete.")
	return nil
}

func copyFile(src, dst string) error {
	in, err := os.Open(src)
	if err != nil {
		return err
	}
	defer in.Close()
	out, err := os.OpenFile(dst, os.O_CREATE|os.O_WRONLY|os.O_TRUNC, 0755)
	if err != nil {
		return err
	}
	defer out.Close()
	if _, err := io.Copy(out, in); err != nil {
		return err
	}
	return out.Close()
}
