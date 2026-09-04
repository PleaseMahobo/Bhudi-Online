//go:build windows

package main

import (
	"os"
	"os/exec"

	"github.com/lxn/walk"
)

func runInstallerGUI() {
	mw, err := walk.NewMainWindow()
	if err != nil {
		walk.MsgBox(nil, "Bhudi Agent Setup", "Unable to start the installer:\r\n"+err.Error(), walk.MsgBoxIconError)
		return
	}
	defer mw.Dispose()

	mw.SetTitle("Bhudi Agent Setup")
	mw.SetSize(walk.Size{Width: 620, Height: 400})
	mw.SetMinMaxSize(walk.Size{Width: 620, Height: 400}, walk.Size{Width: 620, Height: 400})
	_ = mw.SetLayout(walk.NewVBoxLayout())

	title, _ := walk.NewLabel(mw)
	title.SetText("Bhudi Agent Setup")
	titleFont, err := walk.NewFont("Segoe UI", 18, walk.FontBold)
	if err == nil {
		title.SetFont(titleFont)
	}
	title.SetTextAlignment(walk.AlignNear)

	body, _ := walk.NewLabel(mw)
	bodyFont, err := walk.NewFont("Segoe UI", 10, 0)
	if err == nil {
		body.SetFont(bodyFont)
	}
	body.SetText("Welcome to the Bhudi Agent Setup Wizard.\r\n\r\nThis wizard installs and enrolls the Bhudi endpoint agent and registers the Windows service.\r\n\r\nClick Next to continue.")
	body.SetMinMaxSize(walk.Size{Width: 540, Height: 180}, walk.Size{Width: 540, Height: 180})

	status, _ := walk.NewLabel(mw)
	status.SetText("")

	progress, _ := walk.NewProgressBar(mw)
	progress.SetVisible(false)

	buttons, _ := walk.NewComposite(mw)
	_ = buttons.SetLayout(walk.NewHBoxLayout())
	back, _ := walk.NewPushButton(buttons)
	back.SetText("< Back")
	back.SetEnabled(false)
	next, _ := walk.NewPushButton(buttons)
	next.SetText("Next >")
	cancel, _ := walk.NewPushButton(buttons)
	cancel.SetText("Cancel")

	page := 0
	var running bool

	back.Clicked().Attach(func() {
		if running || page != 1 { return }
		page = 0
		body.SetText("Welcome to the Bhudi Agent Setup Wizard.\r\n\r\nThis wizard installs and enrolls the Bhudi endpoint agent and registers the Windows service.\r\n\r\nClick Next to continue.")
		back.SetEnabled(false)
		next.SetText("Next >")
	})

	cancel.Clicked().Attach(func() { mw.Close() })

	next.Clicked().Attach(func() {
		if next.Text() == "Finish" || next.Text() == "Close" { mw.Close(); return }
		if page == 0 {
			page = 1
			body.SetText("The installer is ready to install the Bhudi Agent on this computer.\r\n\r\nThe customer enrollment payload embedded in this installer will be used. No credentials will be displayed.")
			back.SetEnabled(true)
			next.SetText("Install")
			return
		}
		if page != 1 || running { return }

		running = true
		back.SetEnabled(false)
		cancel.SetEnabled(false)
		next.SetEnabled(false)
		next.SetText("Installing...")
		body.SetText("Installing Bhudi Agent...\r\n\r\nPlease wait while the endpoint is enrolled and the Windows service is registered.")
		status.SetText("Starting installation worker...")
		progress.SetVisible(true)
		progress.SetMarqueeMode(true)

		go func() {
			exe, e := os.Executable()
			if e == nil {
				cmd := exec.Command(exe, "install-worker")
				e = cmd.Run()
			}
			mw.Synchronize(func() {
				running = false
				progress.SetMarqueeMode(false)
				progress.SetVisible(false)
				next.SetEnabled(true)
				if e != nil {
					status.SetText("Installation failed.")
					body.SetText("Bhudi Agent Setup could not complete the installation.\r\n\r\n" + e.Error())
					next.SetText("Close")
					return
				}
				status.SetText("Installation completed successfully.")
				body.SetText("Bhudi Agent Setup completed successfully.\r\n\r\nThe Bhudi Agent is enrolled and the Windows service has been installed.")
				next.SetText("Finish")
			})
		}()
	})

	mw.Run()
}
