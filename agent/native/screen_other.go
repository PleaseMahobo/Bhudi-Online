//go:build !windows

package main

import (
	"fmt"
	"image"
	"os/exec"
	"runtime"
)

func primaryDisplayBounds() (image.Rectangle, error) {
	return image.Rect(0, 0, 1280, 720), nil
}

func capturePrimaryScreen() (image.Image, error) {
	tmp := "/tmp/bhudi-screen.png"
	var cmd *exec.Cmd
	switch runtime.GOOS {
	case "darwin":
		cmd = exec.Command("screencapture", "-x", tmp)
	default:
		if _, err := exec.LookPath("import"); err == nil {
			cmd = exec.Command("import", "-window", "root", tmp)
		} else if _, err := exec.LookPath("scrot"); err == nil {
			cmd = exec.Command("scrot", tmp)
		} else if _, err := exec.LookPath("gnome-screenshot"); err == nil {
			cmd = exec.Command("gnome-screenshot", "-f", tmp)
		} else {
			return nil, fmt.Errorf("screen capture requires ImageMagick import, scrot, or gnome-screenshot on Linux")
		}
	}
	if out, err := cmd.CombinedOutput(); err != nil {
		return nil, fmt.Errorf("screenshot tool failed: %v (%s)", err, string(out))
	}
	return loadImageFile(tmp)
}

func applyDesktopInput(ev map[string]any, bounds image.Rectangle) {
	// Input injection on non-Windows is not implemented in this build.
}
