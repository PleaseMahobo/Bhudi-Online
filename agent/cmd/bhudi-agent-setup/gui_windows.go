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

// runInstallerGUI uses native MessageBox only.
// Avoids github.com/lxn/walk (TTM_ADDTOOL failures on some Windows hosts).
func runInstallerGUI() {
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

	// Inform user work is starting (worker is silent / no console window).
	_ = messageBox(
		"Installing Bhudi Agent…\r\n\r\nPlease wait. This may take a minute.\r\n"+
			"(Windows may ask for administrator permission.)",
		"Bhudi Agent Setup",
		mbOK|mbIconInformation,
	)

	err := runInstallWorkerProcess()
	if err != nil {
		_ = messageBox(
			"Installation failed.\r\n\r\n"+err.Error()+"\r\n\r\n"+
				"Tips:\r\n"+
				"  • Run as Administrator\r\n"+
				"  • Download a fresh installer from the Bhudi portal\r\n"+
				"  • Check that the PC can reach the Bhudi API",
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
		if msg == "" {
			msg = err.Error()
		}
		// Prefer the ERROR: line from the worker if present.
		for _, line := range strings.Split(msg, "\n") {
			line = strings.TrimSpace(line)
			if strings.HasPrefix(line, "ERROR:") {
				return fmt.Errorf("%s", strings.TrimSpace(strings.TrimPrefix(line, "ERROR:")))
			}
		}
		return fmt.Errorf("%s", msg)
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
