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

	kernel32                         = syscall.NewLazyDLL("kernel32.dll")
	wtsapi32                         = syscall.NewLazyDLL("wtsapi32.dll")
	procWTSGetActiveConsoleSessionId = kernel32.NewProc("WTSGetActiveConsoleSessionId")
	procWTSQueryUserToken            = wtsapi32.NewProc("WTSQueryUserToken")
	procGetCurrentProcessId         = kernel32.NewProc("GetCurrentProcessId")
	procProcessIdToSessionId        = kernel32.NewProc("ProcessIdToSessionId")

	desktopMu      sync.Mutex
	attachedDesk   uintptr
	attachedWinsta uintptr
	desktopReady   bool
	desktopLastErr string
	desktopKind    string
	desktopWinstaErr string
	desktopCandidateErr string
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
	maximumAllowed         = 0x02000000
	winstaAllAccess        = 0x37F
	genericAll             = 0x10000000
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

func consoleHasUser() bool {
	sid := activeConsoleSessionID()
	if sid == 0xFFFFFFFF {
		return false
	}
	var token syscall.Handle
	r, _, _ := procWTSQueryUserToken.Call(uintptr(sid), uintptr(unsafe.Pointer(&token)))
	if r == 0 {
		return false
	}
	_ = syscall.CloseHandle(token)
	return true
}

func openNamedDesktop(name string, access uintptr) (uintptr, error) {
	n := utf16Ptr(name)
	h, _, err := procOpenDesktopW.Call(uintptr(unsafe.Pointer(n)), 0, 0, access)
	if h == 0 {
		h, _, err = procOpenDesktopW.Call(uintptr(unsafe.Pointer(n)), 0, 0, maximumAllowed)
	}
	if h == 0 {
		h, _, err = procOpenDesktopW.Call(uintptr(unsafe.Pointer(n)), 0, 0, genericAll)
	}
	if h == 0 {
		return 0, err
	}
	return h, nil
}

// ensureInteractiveDesktop switches this OS thread onto WinSta0 and the best
// available interactive desktop (input → Default → Winlogon → Screen-saver).
// Callers MUST runtime.LockOSThread() for capture/input.
func ensureInteractiveDesktop() error {
	desktopMu.Lock()
	defer desktopMu.Unlock()

	ensureDPIAware()

	sid := activeConsoleSessionID()
	if sid == 0xFFFFFFFF {
		desktopReady = false
		desktopLastErr = "no active console session (WTSGetActiveConsoleSessionId=0xFFFFFFFF)"
		desktopCandidateErr = ""
		return fmt.Errorf("%s", desktopLastErr)
	}

	winstaName := utf16Ptr("WinSta0")
	hwinsta, _, errW := procOpenWindowStationW.Call(uintptr(unsafe.Pointer(winstaName)), 0, winstaAllAccess)
	if hwinsta == 0 {
		hwinsta, _, errW = procOpenWindowStationW.Call(uintptr(unsafe.Pointer(winstaName)), 0, maximumAllowed)
	}
	if hwinsta == 0 {
		hwinsta, _, errW = procOpenWindowStationW.Call(uintptr(unsafe.Pointer(winstaName)), 0, genericAll)
	}
	if hwinsta != 0 {
		ok, _, errSet := procSetProcessWindowStation.Call(hwinsta)
		if ok == 0 {
			desktopWinstaErr = fmt.Sprintf("SetProcessWindowStation(WinSta0) failed: %v", errSet)
			desktopLastErr = desktopWinstaErr
		} else {
			desktopWinstaErr = ""
			if attachedWinsta != 0 && attachedWinsta != hwinsta {
				procCloseWindowStation.Call(attachedWinsta)
			}
			attachedWinsta = hwinsta
		}
	} else {
		desktopWinstaErr = fmt.Sprintf("OpenWindowStation(WinSta0) failed: %v", errW)
		desktopLastErr = desktopWinstaErr
	}

	access := uintptr(
		desktopReadObjects | desktopWriteObjects | desktopSwitchDesktop |
			desktopCreateWindow | desktopCreateMenu | desktopHookControl |
			desktopJournalRecord | desktopJournalPlayback,
	)

	type candidate struct {
		kind string
		open func() (uintptr, error)
	}
	candidates := []candidate{
		{"input", func() (uintptr, error) {
			h, _, err := procOpenInputDesktop.Call(0, 0, access)
			if h == 0 {
				h, _, err = procOpenInputDesktop.Call(0, 0, maximumAllowed)
			}
			if h == 0 {
				h, _, err = procOpenInputDesktop.Call(0, 0, genericAll)
			}
			if h == 0 {
				return 0, err
			}
			return h, nil
		}},
		{"default", func() (uintptr, error) { return openNamedDesktop("Default", access) }},
		{"winlogon", func() (uintptr, error) { return openNamedDesktop("Winlogon", access) }},
		{"screen-saver", func() (uintptr, error) { return openNamedDesktop("Screen-saver", access) }},
	}

	var lastOpenErr error
	desktopCandidateErr = ""
	for _, c := range candidates {
		h, errOpen := c.open()
		if h == 0 {
			lastOpenErr = errOpen
			desktopCandidateErr = fmt.Sprintf("%s open: %v", c.kind, errOpen)
			continue
		}
		ok, _, errSet := procSetThreadDesktop.Call(h)
		if ok == 0 {
			procCloseDesktop.Call(h)
			lastOpenErr = errSet
			desktopCandidateErr = fmt.Sprintf("%s SetThreadDesktop: %v", c.kind, errSet)
			continue
		}
		if attachedDesk != 0 && attachedDesk != h {
			procCloseDesktop.Call(attachedDesk)
		}
		attachedDesk = h
		desktopReady = true
		desktopKind = c.kind
		desktopLastErr = ""
		desktopCandidateErr = ""
		return nil
	}

	desktopReady = false
	hint := "is a user logged on, or is the login screen visible?"
	if !consoleHasUser() {
		hint = "no interactive user — attempted Winlogon (login screen); open failed"
	}
	desktopLastErr = fmt.Sprintf("desktop attach failed: %v (%s, console_session=%d)", lastOpenErr, hint, sid)
	if desktopCandidateErr == "" { desktopCandidateErr = desktopLastErr }
	return fmt.Errorf("%s", desktopLastErr)
}

func processSessionID() uint32 {
	pid, _, _ := procGetCurrentProcessId.Call()
	var sid uint32
	ok, _, _ := procProcessIdToSessionId.Call(pid, uintptr(unsafe.Pointer(&sid)))
	if ok == 0 { return 0xFFFFFFFF }
	return sid
}

// desktopDiagnostics returns a structured troubleshooting snapshot without
// exposing screen content or credentials.
func desktopDiagnostics() map[string]any {
	desktopMu.Lock()
	defer desktopMu.Unlock()
	consoleSID := activeConsoleSessionID()
	return map[string]any{
		"process_session": processSessionID(),
		"console_session": consoleSID,
		"console_has_user": consoleHasUser(),
		"desktop_ready": desktopReady,
		"desktop_kind": desktopKind,
		"attached_winsta": attachedWinsta != 0,
		"attached_desktop": attachedDesk != 0,
		"winsta_error": desktopWinstaErr,
		"candidate_error": desktopCandidateErr,
		"last_error": desktopLastErr,
	}
}

func desktopStatusNote() string {
	desktopMu.Lock()
	defer desktopMu.Unlock()
	sid := activeConsoleSessionID()
	base := fmt.Sprintf("console_session=%d has_user=%v desktop=%s", sid, consoleHasUser(), desktopKind)
	if desktopReady {
		return base + " attached"
	}
	if desktopLastErr != "" {
		return base + " " + desktopLastErr
	}
	return base + " not attached"
}

func activeConsoleSessionID() uint32 {
	sid, _, _ := procWTSGetActiveConsoleSessionId.Call()
	return uint32(sid)
}
