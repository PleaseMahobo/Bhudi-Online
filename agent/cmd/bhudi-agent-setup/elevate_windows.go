//go:build windows

package main

import (
	"os"
	"syscall"
	"unsafe"
)

var (
	shell32      = syscall.NewLazyDLL("shell32.dll")
	shellExecute = shell32.NewProc("ShellExecuteW")
)

func ensureElevated() {
	if isElevated() {
		return
	}

	exe, err := os.Executable()
	if err != nil {
		return
	}

	verb, err := syscall.UTF16PtrFromString("runas")
	if err != nil {
		return
	}
	file, err := syscall.UTF16PtrFromString(exe)
	if err != nil {
		return
	}

	args := syscall.UTF16PtrFromString(joinWindowsArgs(os.Args[1:]))
	ret, _, _ := shellExecute.Call(
		0,
		uintptr(unsafe.Pointer(verb)),
		uintptr(unsafe.Pointer(file)),
		uintptr(unsafe.Pointer(args)),
		0,
		uintptr(1),
	)
	if ret > 32 {
		os.Exit(0)
	}
}

func isElevated() bool {
	var sid *syscall.SID
	if err := syscall.AllocateAndInitializeSid(
		&syscall.SECURITY_NT_AUTHORITY,
		2,
		syscall.SECURITY_BUILTIN_DOMAIN_RID,
		syscall.DOMAIN_ALIAS_RID_ADMINS,
		0, 0, 0, 0, 0, 0,
		&sid,
	); err != nil {
		return false
	}
	defer syscall.FreeSid(sid)

	token := syscall.Token(0)
	member, err := token.IsMember(sid)
	return err == nil && member
}

func joinWindowsArgs(args []string) string {
	if len(args) == 0 {
		return ""
	}
	out := ""
	for i, arg := range args {
		if i > 0 {
			out += " "
		}
		out += syscall.EscapeArg(arg)
	}
	return out
}
