//go:build windows

package main

import (
	"fmt"
	"sync"
	"syscall"
)

var (
	procOpenInputDesktop = user32.NewProc("OpenInputDesktop")
	procCloseDesktop     = user32.NewProc("CloseDesktop")
	procSetThreadDesktop = user32.NewProc("SetThreadDesktop")
	procGetThreadDesktop = user32.NewProc("GetThreadDesktop")

	kernel32 = syscall.NewLazyDLL("kernel32.dll")

	desktopMu      sync.Mutex
	attachedDesk  uintptr
	desktopReady  bool
	desktopLastErr string
)

const (
	desktopReadObjects   = 0x0001
	desktopWriteObjects  = 0x0002
	desktopSwitchDesktop = 0x0100
	maximumAllowed      = 0x02000000
)

// ensureInteractiveDesktop attaches this thread to the active Winlogon input
// desktop so GDI capture works even when the process started in Session 0 /
// as a service. Safe to call repeatedly.
func ensureInteractiveDesktop() error {
	desktopMu.Lock()
	defer desktopMu.Unlock()

	access := uintptr(desktopReadObjects | desktopWriteObjects | desktopSwitchDesktop | 0x0004 | 0x0008 | 0x0010 | 0x0020 | 0x0040)
	h, _, errOpen := procOpenInputDesktop.Call(0, 0, access)
	if h == 0 {
		h, _, errOpen = procOpenInputDesktop.Call(0, 0, maximumAllowed)
	}
	if h == 0 {
		desktopReady = false
		desktopLastErr = fmt.Sprintf("OpenInputDesktop failed: %v", errOpen)
		return fmt.Errorf("%s (is a user logged on to the console?)", desktopLastErr)
	}

	ok, _, errSet := procSetThreadDesktop.Call(h)
	if ok == 0 {
		procCloseDesktop.Call(h)
		desktopReady = false
		desktopLastErr = fmt.Sprintf("SetThreadDesktop failed: %v", errSet)
		return fmt.Errorf("%s", desktopLastErr)
	}

	if attachedDesk != 0 && attachedDesk != h {
		procCloseDesktop.Call(attachedDesk)
	}
	attachedDesk = h
	desktopReady = true
	desktopLastErr = ""
	return nil
}

func desktopStatusNote() string {
	desktopMu.Lock()
	defer desktopMu.Unlock()
	if desktopReady {
		return "input-desktop attached"
	}
	if desktopLastErr != "" {
		return desktopLastErr
	}
	return "input-desktop not attached"
}
