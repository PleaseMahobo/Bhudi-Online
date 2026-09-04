//go:build windows

package main

import (
	"os"
	"os/exec"
	"syscall"
	"unsafe"
)

var (
	shell32      = syscall.NewLazyDLL("shell32.dll")
	shellExecute = shell32.NewProc("ShellExecuteW")
)

func ensureElevated() {
	if os.Getenv("BHUDI_SETUP_ELEVATED") == "1" {
		return
	}
	if err := exec.Command("net", "session").Run(); err == nil {
		return
	}

	exe, err := os.Executable()
	if err != nil {
		os.Exit(1)
	}

	verb, _ := syscall.UTF16PtrFromString("runas")
	file, _ := syscall.UTF16PtrFromString(exe)
	params, _ := syscall.UTF16PtrFromString("")
	dir, _ := syscall.UTF16PtrFromString("")

	ret, _, _ := shellExecute.Call(
		0,
		uintptr(unsafe.Pointer(verb)),
		uintptr(unsafe.Pointer(file)),
		uintptr(unsafe.Pointer(params)),
		uintptr(unsafe.Pointer(dir)),
		uintptr(1),
	)
	if ret <= 32 {
		os.Exit(1)
	}
	os.Exit(0)
}
