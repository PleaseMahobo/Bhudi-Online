//go:build windows

package main

import (
	"fmt"
	"os"
	"os/exec"
	"strings"
	"syscall"
	"unsafe"

	"golang.org/x/sys/windows"
)

func runInstallerGUI() {
	if !isElevated() {
		if err := relaunchElevated(); err != nil {
			_ = messageBox(
				"Administrator permission is required to install the Bhudi Agent.\r\n\r\n"+err.Error(),
				"Bhudi Agent Setup",
				mbOK|mbIconError,
			)
		}
		return
	}

	welcome := "Bhudi Agent Setup\r\n\r\n" +
		"A Big Brother's Approach to Remote Monitoring and Management\r\n\r\n" +
		"This customer installer will:\r\n" +
		"  • Enroll this PC to your Bhudi tenant\r\n" +
		"  • Install the monitoring agent (Windows service)\r\n" +
		"  • Install the Support Client (tray + tickets)\r\n\r\n" +
		"Click Yes to install now.\r\n" +
		"Click No to cancel."

	if messageBox(welcome, "Bhudi Agent Setup", mbYesNo|mbIconQuestion) != idYes {
		return
	}

	_ = messageBox(
		"Installing Bhudi Agent…\r\n\r\nPlease wait. This may take a minute.",
		"Bhudi Agent Setup",
		mbOK|mbIconInformation,
	)

	if err := runInstallWorkerProcess(); err != nil {
		_ = messageBox(
			"Installation failed.\r\n\r\n"+err.Error()+"\r\n\r\n"+
				"Installer log: C:\\ProgramData\\Bhudi\\Logs\\installer.log\r\n\r\n"+
				"Please use the exact error and log when reporting this issue.",
			"Bhudi Agent Setup",
			mbOK|mbIconError,
		)
		return
	}

	_ = messageBox(
		"Installation completed successfully.\r\n\r\n"+
			"This device is enrolled and monitored.\r\n"+
			"The BhudiAgent service and Support Client are installed.\r\n\r\n"+
			"Open the Bhudi portal to manage this device.",
		"Bhudi Agent Setup",
		mbOK|mbIconInformation,
	)
}

func isElevated() bool {
	shell32 := windows.NewLazySystemDLL("shell32.dll")
	proc := shell32.NewProc("IsUserAnAdmin")
	r, _, _ := proc.Call()
	return r != 0
}

func relaunchElevated() error {
	exe, err := os.Executable()
	if err != nil {
		return err
	}
	shell32 := windows.NewLazySystemDLL("shell32.dll")
	proc := shell32.NewProc("ShellExecuteW")
	r, _, callErr := proc.Call(
		0,
		uintptr(unsafe.Pointer(windows.StringToUTF16Ptr("runas"))),
		uintptr(unsafe.Pointer(windows.StringToUTF16Ptr(exe))),
		uintptr(unsafe.Pointer(windows.StringToUTF16Ptr("elevated-ui"))),
		0,
		1,
	)
	if r <= 32 {
		if callErr != nil && callErr != syscall.Errno(0) {
			return fmt.Errorf("elevation was cancelled or failed: %v", callErr)
		}
		return fmt.Errorf("elevation was cancelled or failed (ShellExecute code %d)", r)
	}
	return nil
}

func runInstallWorkerProcess() error {
	exe, err := os.Executable()
	if err != nil {
		return err
	}
	cmd := exec.Command(exe, "install-worker")
	cmd.SysProcAttr = &syscall.SysProcAttr{HideWindow: true}
	out, err := cmd.CombinedOutput()
	if err != nil {
		msg := strings.TrimSpace(string(out))
		for _, line := range strings.Split(msg, "\n") {
			line = strings.TrimSpace(line)
			if strings.HasPrefix(line, "ERROR:") {
				return fmt.Errorf("%s", strings.TrimSpace(strings.TrimPrefix(line, "ERROR:")))
			}
		}
		if msg != "" {
			return fmt.Errorf("%s", msg)
		}
		return fmt.Errorf("installer worker failed: %w", err)
	}
	return nil
}

const (
	mbOK              = 0x00000000
	mbYesNo           = 0x00000004
	mbIconError       = 0x00000010
	mbIconQuestion    = 0x00000020
	mbIconInformation = 0x00000040
	idYes             = 6
)

func messageBox(text, title string, flags uint) int {
	user32 := windows.NewLazySystemDLL("user32.dll")
	proc := user32.NewProc("MessageBoxW")
	r, _, _ := proc.Call(
		0,
		uintptr(unsafe.Pointer(windows.StringToUTF16Ptr(text))),
		uintptr(unsafe.Pointer(windows.StringToUTF16Ptr(title))),
		uintptr(flags),
	)
	return int(r)
}
