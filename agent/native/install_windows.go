//go:build windows

package main

import (
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"syscall"
	"time"

	"golang.org/x/sys/windows/registry"
)

const (
	windowsServiceName  = "BhudiAgent"
	windowsTaskName     = "BhudiAgent"
	windowsWatchdogName = "BhudiAgentWatchdog"
	windowsSupportTask  = "BhudiSupport"
	supportExeName      = "bhudi-support.exe"
	uninstallRegPath    = `SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\BhudiAgent`
	displayName         = "Bhudi Agent"
	publisherName       = "Bhudi"
	runKeyPath          = `Software\Microsoft\Windows\CurrentVersion\Run`
)

func installService(server string) (err error) {
	defer func() {
		if r := recover(); r != nil {
			err = fmt.Errorf("install panic: %v", r)
			logInstall("install FAILED (panic): %v", r)
		}
	}()

	server = strings.TrimRight(server, "/")
	logInstall("install: resolving executable")
	exe, err := os.Executable()
	if err != nil {
		return fmt.Errorf("executable path: %w", err)
	}
	exe, err = filepath.Abs(exe)
	if err != nil {
		return fmt.Errorf("abs path: %w", err)
	}
	logInstall("install: source=%s pid=%d", exe, os.Getpid())

	candidates := []string{}
	if pd := os.Getenv("ProgramData"); pd != "" {
		candidates = append(candidates, filepath.Join(pd, "Bhudi", "Agent"))
	}
	if pf := os.Getenv("ProgramFiles"); pf != "" {
		candidates = append(candidates, filepath.Join(pf, "Bhudi", "Agent"))
	}
	if la := os.Getenv("LOCALAPPDATA"); la != "" {
		candidates = append(candidates, filepath.Join(la, "Bhudi", "Agent"))
	}
	if len(candidates) == 0 {
		return fmt.Errorf("no install directory candidates (ProgramData/ProgramFiles unset)")
	}

	var destDir, dest string
	var lastMkErr error
	for _, dir := range candidates {
		logInstall("install: try dir %s", dir)
		if err := os.MkdirAll(dir, 0755); err != nil {
			lastMkErr = err
			logInstall("install: mkdir failed: %v", err)
			continue
		}
		destDir = dir
		dest = filepath.Join(dir, "bhudi-agent.exe")
		break
	}
	if destDir == "" {
		return fmt.Errorf("create install dir: %w", lastMkErr)
	}
	logInstall("install: dest=%s", dest)

	logInstall("install: stop existing agent if present")
	if err := stopBhudiForUpgrade(dest); err != nil {
		if pf := os.Getenv("ProgramFiles"); pf != "" {
			_ = stopBhudiForUpgrade(filepath.Join(pf, "Bhudi", "Agent", "bhudi-agent.exe"))
		}
		logInstall("install: prepare upgrade warning: %v (continuing)", err)
	}

	sameBinary := strings.EqualFold(filepath.Clean(exe), filepath.Clean(dest))
	if sameBinary {
		logInstall("install: source already at dest — skip copy")
	} else {
		logInstall("install: copying binary")
		if err := copyFile(exe, dest); err != nil {
			_ = killOtherBhudiAgents()
			time.Sleep(time.Second)
			if err2 := copyFile(exe, dest); err2 != nil {
				return fmt.Errorf("copy agent to %s: %w", dest, err2)
			}
		}
		logInstall("install: binary copied OK")
	}

	if err := writeConfig(server); err != nil {
		fmt.Println("Warning: could not write config:", err)
		logInstall("install: config warning: %v", err)
	}

	if err := installSupportClient(destDir); err != nil {
		fmt.Println("Warning: support client:", err)
		logInstall("install: support client warning: %v", err)
	}

	logInstall("install: registering Windows service")
	if err := installWindowsService(dest, server); err != nil {
		fmt.Printf("Warning: Windows Service install failed: %v\n", err)
		logInstall("install: service warning: %v", err)
		fmt.Println("Falling back to ONSTART scheduled task...")
		if err2 := installOnStartTask(dest, server); err2 != nil {
			fmt.Printf("Warning: ONSTART task failed: %v\n", err2)
			logInstall("install: onstart warning: %v", err2)
		}
	} else {
		fmt.Println("Windows Service installed:", windowsServiceName, "(Start=Automatic)")
		logInstall("install: service OK")
	}

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
		fmt.Println("Service start deferred; starting process directly:", err)
		logInstall("install: service start deferred: %v", err)
		if err := startDetached(dest, server); err != nil {
			fmt.Println("Warning: could not start agent now:", err)
			logInstall("install: detached start failed: %v", err)
		} else {
			fmt.Println("Agent started in the background.")
		}
	} else {
		fmt.Println("Service started.")
		logInstall("install: service started")
	}

	fmt.Println()
	fmt.Println("Install complete — install once; agent starts at every boot.")
	fmt.Println("  Binary:   ", dest)
	fmt.Println("  Server:   ", server)
	fmt.Println("  Identity: ", identityPath())
	fmt.Println("  Service:  ", windowsServiceName, "(Automatic)")
	fmt.Println("  Support:  ", filepath.Join(destDir, supportExeName), "(tray / tickets)")
	logInstall("install OK dest=%s", dest)
	time.Sleep(1 * time.Second)
	return nil
}

func killOtherBhudiAgents() error {
	self := os.Getpid()
	out, err := exec.Command("tasklist", "/FI", "IMAGENAME eq bhudi-agent.exe", "/FO", "CSV", "/NH").CombinedOutput()
	if err != nil {
		return err
	}
	for _, line := range strings.Split(string(out), "\n") {
		line = strings.TrimSpace(line)
		if line == "" || !strings.Contains(strings.ToLower(line), "bhudi-agent") {
			continue
		}
		parts := strings.Split(line, ",")
		if len(parts) < 2 {
			continue
		}
		pidStr := strings.Trim(parts[1], "\" ")
		pid, err := strconv.Atoi(pidStr)
		if err != nil || pid <= 0 || pid == self {
			continue
		}
		logInstall("install: killing other agent pid=%d", pid)
		_ = exec.Command("taskkill", "/F", "/PID", strconv.Itoa(pid)).Run()
	}
	_ = exec.Command("taskkill", "/F", "/IM", "bhudi-support.exe").Run()
	return nil
}

func installSupportClient(destDir string) error {
	srcCandidates := []string{}
	if exe, err := os.Executable(); err == nil {
		srcCandidates = append(srcCandidates, filepath.Join(filepath.Dir(exe), supportExeName))
	}
	if wd, err := os.Getwd(); err == nil {
		srcCandidates = append(srcCandidates, filepath.Join(wd, supportExeName))
	}
	srcCandidates = append(srcCandidates, filepath.Join(destDir, supportExeName))

	var src string
	for _, c := range srcCandidates {
		if st, err := os.Stat(c); err == nil && !st.IsDir() {
			src = c
			break
		}
	}
	if src == "" {
		return fmt.Errorf("%s not found next to installer — tray tickets skipped", supportExeName)
	}
	dest := filepath.Join(destDir, supportExeName)
	if src != dest {
		if err := copyFile(src, dest); err != nil {
			return fmt.Errorf("copy support client: %w", err)
		}
	}
	logInstall("support client installed: %s", dest)

	_ = exec.Command("schtasks", "/Delete", "/TN", windowsSupportTask, "/F").Run()
	tr := fmt.Sprintf("\"%s\"", dest)
	create := exec.Command("schtasks", "/Create", "/TN", windowsSupportTask,
		"/TR", tr, "/SC", "ONLOGON", "/RL", "LIMITED", "/F")
	if out, err := create.CombinedOutput(); err != nil {
		fmt.Printf("Warning: support logon task failed: %v (%s)\n", err, strings.TrimSpace(string(out)))
	} else {
		fmt.Println("Support tray logon task:", windowsSupportTask)
	}

	if key, _, err := registry.CreateKey(registry.CURRENT_USER, runKeyPath, registry.SET_VALUE); err == nil {
		_ = key.SetStringValue("BhudiSupport", fmt.Sprintf("\"%s\"", dest))
		key.Close()
		fmt.Println("Support Run key registered (current user).")
	}

	cmd := exec.Command(dest)
	cmd.Stdout = nil
	cmd.Stderr = nil
	cmd.Stdin = nil
	cmd.SysProcAttr = &syscall.SysProcAttr{
		CreationFlags: 0x00000008 | 0x00000200,
		HideWindow:    true,
	}
	_ = cmd.Start()
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

func stopBhudiForUpgrade(dest string) error {
	_ = exec.Command("schtasks", "/Delete", "/TN", windowsWatchdogName, "/F").Run()
	_ = exec.Command("schtasks", "/Delete", "/TN", windowsTaskName, "/F").Run()
	_ = exec.Command("sc", "stop", windowsServiceName).Run()

	deadline := time.Now().Add(10 * time.Second)
	for time.Now().Before(deadline) {
		out, _ := exec.Command("sc", "query", windowsServiceName).CombinedOutput()
		if strings.Contains(string(out), "STOPPED") || !strings.Contains(string(out), "RUNNING") {
			break
		}
		time.Sleep(400 * time.Millisecond)
	}

	_ = killOtherBhudiAgents()
	time.Sleep(400 * time.Millisecond)

	if dest == "" {
		return nil
	}
	for i := 0; i < 15; i++ {
		if _, err := os.Stat(dest); os.IsNotExist(err) {
			return nil
		}
		fh, err := os.OpenFile(dest, os.O_WRONLY|os.O_APPEND, 0)
		if err == nil {
			_ = fh.Close()
			return nil
		}
		time.Sleep(400 * time.Millisecond)
	}

	backup := dest + ".old." + time.Now().Format("20060102-150405")
	if err := os.Rename(dest, backup); err != nil {
		logInstall("prepare upgrade: rename locked binary failed: %v", err)
		_ = os.Remove(dest)
		if _, err2 := os.Stat(dest); err2 == nil {
			return fmt.Errorf("existing agent binary remained locked: %s (%v)", dest, err)
		}
		return nil
	}
	logInstall("prepare upgrade: renamed locked binary to %s", backup)
	return nil
}

func installWindowsService(dest, server string) error {
	_ = exec.Command("sc", "stop", windowsServiceName).Run()
	_ = exec.Command("sc", "delete", windowsServiceName).Run()
	time.Sleep(500 * time.Millisecond)

	binPath := fmt.Sprintf("\"%s\" run -server %s", dest, server)
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
	_ = key.SetDWordValue("EstimatedSize", 12288)
	return nil
}

func uninstallService() error {
	logInstall("uninstall: stopping service %s", windowsServiceName)
	_ = exec.Command("sc", "stop", windowsServiceName).Run()
	_ = exec.Command("sc", "delete", windowsServiceName).Run()
	fmt.Println("Windows Service removed:", windowsServiceName)

	_ = exec.Command("schtasks", "/Delete", "/TN", windowsTaskName, "/F").Run()
	_ = exec.Command("schtasks", "/Delete", "/TN", windowsWatchdogName, "/F").Run()
	_ = exec.Command("schtasks", "/Delete", "/TN", windowsSupportTask, "/F").Run()
	fmt.Println("Scheduled tasks removed (agent + support).")

	if key, err := registry.OpenKey(registry.CURRENT_USER, runKeyPath, registry.SET_VALUE); err == nil {
		_ = key.DeleteValue("BhudiAgent")
		_ = key.DeleteValue("BhudiSupport")
		key.Close()
	}
	_ = registry.DeleteKey(registry.LOCAL_MACHINE, uninstallRegPath)
	_ = registry.DeleteKey(registry.CURRENT_USER, uninstallRegPath)
	fmt.Println("Startup and uninstall registry cleaned.")
	fmt.Println("Uninstall complete.")
	return nil
}

func copyFile(src, dst string) error {
	if strings.EqualFold(filepath.Clean(src), filepath.Clean(dst)) {
		return nil
	}
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
