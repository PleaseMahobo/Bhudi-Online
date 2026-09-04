//go:build windows

package main

import (
	"bytes"
	"encoding/base64"
	"image"
	_ "image/png"
	"os"
	"os/exec"
	"path/filepath"

	"github.com/lxn/walk"
)

// logoPNGBase64 is populated from logo_embed.go (or left empty for text-only UI).
var logoPNGBase64 string

func runInstallerGUI() {
	mw, err := walk.NewMainWindow()
	if err != nil {
		walk.MsgBox(nil, "Bhudi Agent Setup", "Unable to start the installer:\r\n"+err.Error(), walk.MsgBoxIconError)
		return
	}
	defer mw.Dispose()

	mw.SetTitle("Bhudi Agent Setup")
	mw.SetSize(walk.Size{Width: 680, Height: 520})
	mw.SetMinMaxSize(walk.Size{Width: 680, Height: 520}, walk.Size{Width: 720, Height: 560})
	_ = mw.SetLayout(walk.NewVBoxLayout())

	if logoPNGBase64 != "" {
		if img, e := loadEmbeddedLogo(); e == nil && img != nil {
			if iv, e2 := walk.NewImageView(mw); e2 == nil {
				_ = iv.SetImage(img)
				iv.SetMode(walk.ImageViewModeShrink)
				iv.SetMinMaxSize(walk.Size{Width: 120, Height: 120}, walk.Size{Width: 140, Height: 140})
			}
		}
	}

	title, _ := walk.NewLabel(mw)
	title.SetText("Bhudi Agent Setup")
	if f, e := walk.NewFont("Segoe UI", 18, walk.FontBold); e == nil {
		title.SetFont(f)
	}
	title.SetTextAlignment(walk.AlignNear)

	slogan, _ := walk.NewLabel(mw)
	if f, e := walk.NewFont("Segoe UI", 10, walk.FontItalic); e == nil {
		slogan.SetFont(f)
	}
	slogan.SetText("A Big Brother's Approach to Remote Monitoring and Management")
	slogan.SetTextAlignment(walk.AlignNear)

	body, _ := walk.NewLabel(mw)
	if f, e := walk.NewFont("Segoe UI", 10, 0); e == nil {
		body.SetFont(f)
	}
	body.SetText(welcomeText)
	body.SetMinMaxSize(walk.Size{Width: 600, Height: 200}, walk.Size{Width: 620, Height: 220})

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
		if running || page != 1 {
			return
		}
		page = 0
		body.SetText(welcomeText)
		back.SetEnabled(false)
		next.SetText("Next >")
	})

	cancel.Clicked().Attach(func() { mw.Close() })

	next.Clicked().Attach(func() {
		if next.Text() == "Finish" || next.Text() == "Close" {
			mw.Close()
			return
		}
		if page == 0 {
			page = 1
			body.SetText(readyText)
			back.SetEnabled(true)
			next.SetText("Install")
			return
		}
		if page != 1 || running {
			return
		}

		running = true
		back.SetEnabled(false)
		cancel.SetEnabled(false)
		next.SetEnabled(false)
		next.SetText("Installing...")
		body.SetText(installingText)
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
				body.SetText(successText)
				next.SetText("Finish")
			})
		}()
	})

	mw.Run()
}

const welcomeText = `Welcome to the Bhudi Agent Setup Wizard.

This customer-specific installer will:
  • Enroll this device to your Bhudi tenant
  • Install the always-on monitoring agent (service)
  • Install the Support Client (tray + ticketing)
  • Enable remote monitoring, inventory, scripts, and ITSM tickets

Click Next to continue.`

const readyText = `Ready to install Bhudi Agent on this computer.

What you get:
  • Full device monitoring & heartbeat
  • Remote commands and inventory
  • End-user ticketing (system tray)
  • Patch & policy readiness via the Bhudi platform

Enrollment is automatic using the secure token embedded in this installer.
No credentials are shown on screen.`

const installingText = `Installing Bhudi Agent…

Please wait while:
  1. The endpoint is enrolled to your tenant
  2. The Windows service is registered
  3. The Support Client (ticketing tray) is installed`

const successText = `Bhudi Agent Setup completed successfully.

This device is now:
  • Enrolled and monitored
  • Running the BhudiAgent Windows service
  • Equipped with the Support Client for ticketing

Technicians can manage monitoring, remote access, scripts and tickets from the Bhudi portal.`

func loadEmbeddedLogo() (walk.Image, error) {
	if logoPNGBase64 == "" {
		return nil, os.ErrNotExist
	}
	raw, err := base64.StdEncoding.DecodeString(logoPNGBase64)
	if err != nil {
		return nil, err
	}
	if _, _, err := image.Decode(bytes.NewReader(raw)); err != nil {
		return nil, err
	}
	tmp := filepath.Join(os.TempDir(), "bhudi-setup-logo.png")
	if err := os.WriteFile(tmp, raw, 0644); err != nil {
		return nil, err
	}
	return walk.NewImageFromFile(tmp)
}
