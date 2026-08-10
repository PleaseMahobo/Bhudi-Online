//go:build windows

package main

import (
	"fmt"
	"sync"
	"syscall"
	"unsafe"
)

var (
	procOpenInputDesktop        = user32.NewProc("OpenInputDesktop")
	procOpenDesktopW            = user32.NewProc("OpenDesktopW")
	procCloseDesktop            = user32.NewProc("CloseDesktop")
	procSetThreadDesktop        = user32.NewProc("SetThreadDesktop")
	procGetThreadDesktop        = user32.NewProc("GetThreadDesktop")
	procOpenWindowStationW      = user32.NewProc("OpenWindowStationW")
	procSetProcessWindowStation = user32.NewProc("SetProcessWindowStation")
	procGetProcessWindowStation = user32.NewProc("GetProcessWindowStation")
	procCloseWindowStation      = user32.NewProc("CloseWindowStation")
	procSetProcessDPIAware      = user32.NewProc("SetProcessDPIAware")

	kernel32                           = syscall.NewLazyDLL("kernel32.dll")
	wtsapi32                           = syscall.NewLazyDLL("wtsapi32.dll")
	procWTSGetActiveConsoleSessionId = kernel32.NewProc("WTSGetActiveConsoleSessionId")

	desktopMu      sync.Mutex
	attachedDesk   uintptr
	attachedWinsta uintptr
	desktopReady   bool
	desktopLastErr string
	dpiAwareOnce   sync.Once
)

const (
	desktopReadObjects     = 0x0001
	desktopWriteObjects    = 0x0002
	desktopSwitchDesktop   = 0x0100
	desktopCreateWindow    = 0x0004
	desktopCreateMenu      = 0x0008
	desktopHookControl     = 0x0010
	desktopJournalRecord   = 0x0020
	desktopJournalPlayback = 0x0040
	maximumAllowed        = 0x02000000
	winstaAllAccess       = 0x37F
)

func utf16Ptr(s string) *uint16 {
	p, _ := syscall.UTF16PtrFromString(s)
	return p
}

func ensureDPIAware() {
	dpiAwareOnce.Do(func() {
		_, _, _ = procSetProcessDPIAware.Call()
	})
}

// ensureInteractiveDesktop switches this process/thread onto WinSta0 and the
// active input desktop so BitBlt/GetDC see the user's interactive session.
func ensureInteractiveDesktop() error {
	desktopMu.Lock()
	defer desktopMu.Unlock()

	ensureDPIAware()

	winstaName := utf16Ptr("WinSta0")
	hwinsta, _, errW := procOpenWindowStationW.Call(
		uintptr(unsafe.Pointer(winstaName)),
		0,
		winstaAllAccess,
	)
	if hwinsta == 0 {
		hwinsta, _, errW = procOpenWindowStationW.Call(
			uintptr(unsafe.Pointer(winstaName)),
			0,
			maximumAllowed,
		)
	}
	if hwinsta != 0 {
		ok, _, errSet := procSetProcessWindowStation.Call(hwinsta)
		if ok == 0 {
			desktopLastErr = fmt.Sprintf("SetProcessWindowStation(WinSta0) failed: %v", errSet)
		} else {
			if attachedWinsta != 0 && attachedWinsta != hwinsta {
				procCloseWindowStation.Call(attachedWinsta)
			}
			attachedWinsta = hwinsta
		}
	} else {
		desktopLastErr = fmt.Sprintf("OpenWindowStation(WinSta0) failed: %v", errW)
	}

	access := uintptr(
		desktopReadObjects | desktopWriteObjects | desktopSwitchDesktop |
			desktopCreateWindow | desktopCreateMenu | desktopHookControl |
			desktopJournalRecord | desktopJournalPlayback,
	)

	var h uintptr
	var errOpen error
	h, _, errOpen = procOpenInputDesktop.Call(0, 0, access)
	if h == 0 {
		h, _, errOpen = procOpenInputDesktop.Call(0, 0, maximumAllowed)
	}
	if h == 0 {
		defName := utf16Ptr("Default")
		h, _, errOpen = procOpenDesktopW.Call(
			uintptr(unsafe.Pointer(defName)),
			0,
			0,
			access,
		)
	}
	if h == 0 {
		defName := utf16Ptr("Default")
		h, _, errOpen = procOpenDesktopW.Call(
			uintptr(unsafe.Pointer(defName)),
			0,
			0,
			maximumAllowed,
		)
	}
	if h == 0 {
		desktopReady = false
		desktopLastErr = fmt.Sprintf("OpenInputDesktop/OpenDesktop failed: %v (is a user logged on to the console session?)", errOpen)
		return fmt.Errorf("%s", desktopLastErr)
	}

	ok, _, errSet := procSetThreadDesktop.Call(h)
	if ok == 0 {
		procCloseDesktop.Call(h)
		desktopReady = false
		desktopLastErr = fmt.Sprintf("SetThreadDesktop failed: %v (agent may be locked to Session 0)", errSet)
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
	sid, _, _ := procWTSGetActiveConsoleSessionId.Call()
	base := fmt.Sprintf("console_session=%d", sid)
	if desktopReady {
		return base + " input-desktop attached"
	}
	if desktopLastErr != "" {
		return base + " " + desktopLastErr
	}
	return base + " input-desktop not attached"
}

func activeConsoleSessionID() uint32 {
	sid, _, _ := procWTSGetActiveConsoleSessionId.Call()
	return uint32(sid)
}
