//go:build windows

package main

import (
	"fmt"
	"os"
	"os/exec"
	"syscall"
	"unsafe"

	"github.com/lxn/walk"
	"golang.org/x/sys/windows"
)

// runInstallerGUI shows a simple wizard. If walk fails (e.g. TTM_ADDTOOL on
// some Windows builds), falls back to MessageBox + silent install-worker.
func runInstallerGUI() {
	defer func() {
		if r := recover(); r != nil {
			runMessageBoxInstaller(fmt.Sprintf("%v", r))
		}
	}()

	if err := tryWalkWizard(); err != nil {
		runMessageBoxInstaller(err.Error())
	}
}

func tryWalkWizard() error {
	mw, err := walk.NewMainWindow()
	if err != nil {
		return err
	}
	defer mw.Dispose()

	mw.SetTitle("Bhudi Agent Setup")
	mw.SetSize(walk.Size{Width: 640, Height: 420})
	_ = mw.SetLayout(walk.NewVBoxLayout())

	title, err := walk.NewTextLabel(mw)
	if err != nil {
		return err
	}
	title.SetText("Bhudi Agent Setup")
	if f, e := walk.NewFont("Segoe UI", 16, walk.FontBold); e == nil {
		title.SetFont(f)
	}

	slogan, err := walk.NewTextLabel(mw)
	if err != nil {
		return err
	}
	slogan.SetText("A Big Brother's Approach to Remote Monitoring and Management")

	body, err := walk.NewTextLabel(mw)
	if err != nil {
		return err
	}
	body.SetText(welcomeText)

	status, err := walk.NewTextLabel(mw)
	if err != nil {
		return err
	}
	status.SetText("")

	// Avoid ProgressBar + ToolTip paths that trigger TTM_ADDTOOL on some hosts.
	buttons, err := walk.NewComposite(mw)
	if err != nil {
		return err
	}
	_ = buttons.SetLayout(walk.NewHBoxLayout())

	next, err := walk.NewPushButton(buttons)
	if err != nil {
		return err
	}
	next.SetText("Install")
	next.SetToolTipText("") // explicit empty — reduces tooltip init failures

	cancel, err := walk.NewPushButton(buttons)
	if err != nil {
		return err
	}
	cancel.SetText("Cancel")
	cancel.SetToolTipText("")

	var running bool
	cancel.Clicked().Attach(func() { mw.Close() })
	next.Clicked().Attach(func() {
		if next.Text() == "Finish" || next.Text() == "Close" {
			mw.Close()
			return
		}
		if running {
			return
		}
		running = true
		next.SetEnabled(false)
		cancel.SetEnabled(false)
		next.SetText("Installing...")
		body.SetText(installingText)
		status.SetText("Please wait…")

		go func() {
			errInstall := runInstallWorkerProcess()
			mw.Synchronize(func() {
				running = false
				next.SetEnabled(true)
				if errInstall != nil {
					status.SetText("Installation failed.")
					body.SetText("Could not complete installation.\r\n\r\n" + errInstall.Error())
					next.SetText("Close")
					return
				}
				status.SetText("Done.")
				body.SetText(successText)
				next.SetText("Finish")
			})
		}()
	})

	mw.Run()
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
		msg := stringsTrim(string(out))
		if msg == "" {
			msg = err.Error()
		}
		return fmt.Errorf("%s", msg)
	}
	return nil
}

func stringsTrim(s string) string {
	for len(s) > 0 && (s[0] == ' ' || s[0] == '\n' || s[0] == '\r' || s[0] == '\t') {
		s = s[1:]
	}
	n := len(s)
	for n > 0 && (s[n-1] == ' ' || s[n-1] == '\n' || s[n-1] == '\r' || s[n-1] == '\t') {
		n--
	}
	return s[:n]
}

// runMessageBoxInstaller — reliable path when walk GUI cannot start.
func runMessageBoxInstaller(reason string) {
	msg := "Bhudi Agent Setup\r\n\r\n" +
		"The graphical wizard could not start on this PC\r\n" +
		"(" + truncate(reason, 120) + ").\r\n\r\n" +
		"Click Yes to install using the silent installer.\r\n" +
		"Click No to cancel."
	if messageBoxYesNo("Bhudi Agent Setup", msg) != 6 { // IDYES = 6
		return
	}
	err := runInstallWorkerProcess()
	if err != nil {
		messageBoxOK("Bhudi Agent Setup", "Installation failed:\r\n\r\n"+err.Error())
		return
	}
	messageBoxOK("Bhudi Agent Setup", "Installation completed successfully.\r\n\r\n"+
		"The Bhudi Agent service and Support Client are installed.\r\n"+
		"Check the Bhudi portal for this device.")
}

func truncate(s string, n int) string {
	if len(s) <= n {
		return s
	}
	return s[:n] + "…"
}

func messageBoxOK(title, text string) {
	user32 := windows.NewLazySystemDLL("user32.dll")
	proc := user32.NewProc("MessageBoxW")
	_, _, _ = proc.Call(
		0,
		uintptr(unsafe.Pointer(windows.StringToUTF16Ptr(text))),
		uintptr(unsafe.Pointer(windows.StringToUTF16Ptr(title))),
		0x10|0x0, // MB_ICONERROR | MB_OK for errors; use 0x40 for info below
	)
}

func messageBoxYesNo(title, text string) int {
	user32 := windows.NewLazySystemDLL("user32.dll")
	proc := user32.NewProc("MessageBoxW")
	r, _, _ := proc.Call(
		0,
		uintptr(unsafe.Pointer(windows.StringToUTF16Ptr(text))),
		uintptr(unsafe.Pointer(windows.StringToUTF16Ptr(title))),
		0x24, // MB_YESNO | MB_ICONQUESTION
	)
	return int(r)
}

const welcomeText = `Welcome to Bhudi Agent Setup.

This installer will enroll this PC, install the monitoring service,
and install the Support Client (tray + tickets).

Click Install to continue.`

const installingText = `Installing Bhudi Agent…
Please wait (service + support client).`

const successText = `Installation completed successfully.

This device is enrolled and monitored.
Open the Bhudi portal to manage it.`
