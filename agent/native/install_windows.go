//go:build windows

package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"
)

const windowsTaskName = "BhudiAgent"

func installService(server string) error {
	exe, err := os.Executable()
	if err != nil {
		return err
	}
	exe, _ = filepath.Abs(exe)

	destDir := filepath.Join(os.Getenv("ProgramFiles"), "Bhudi", "Agent")
	if err := os.MkdirAll(destDir, 0755); err != nil {
		destDir = filepath.Join(os.Getenv("LOCALAPPDATA"), "Bhudi", "Agent")
		if err := os.MkdirAll(destDir, 0755); err != nil {
			return err
		}
	}
	dest := filepath.Join(destDir, "bhudi-agent.exe")
	if err := copyFile(exe, dest); err != nil {
		return fmt.Errorf("copy agent: %w", err)
	}
	_ = writeConfig(server)

	cmdLine := fmt.Sprintf("\"%s\" run -server %s", dest, server)
	_ = exec.Command("schtasks", "/Delete", "/TN", windowsTaskName, "/F").Run()
	create := exec.Command("schtasks", "/Create", "/TN", windowsTaskName,
		"/TR", cmdLine, "/SC", "ONLOGON", "/RL", "HIGHEST", "/F")
	out, err := create.CombinedOutput()
	if err != nil {
		return fmt.Errorf("schtasks: %v (%s)", err, strings.TrimSpace(string(out)))
	}
	_ = exec.Command("schtasks", "/Run", "/TN", windowsTaskName).Start()
	start := exec.Command(dest, "run", "-server", server)
	_ = start.Start()

	fmt.Println("Bhudi Agent installed (native — no Python required).")
	fmt.Println("  Binary: ", dest)
	fmt.Println("  Server: ", server)
	fmt.Println("  Task:   ", windowsTaskName)
	time.Sleep(2 * time.Second)
	return nil
}

func uninstallService() error {
	_ = exec.Command("schtasks", "/Delete", "/TN", windowsTaskName, "/F").Run()
	fmt.Println("Scheduled task removed:", windowsTaskName)
	return nil
}

func copyFile(src, dst string) error {
	in, err := os.ReadFile(src)
	if err != nil {
		return err
	}
	return os.WriteFile(dst, in, 0755)
}
