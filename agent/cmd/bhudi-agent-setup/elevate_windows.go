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

	args, err := syscall.UTF16PtrFromString(joinWindowsArgs(os.Args[1:]))
	if err != nil {
		return
	}
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
