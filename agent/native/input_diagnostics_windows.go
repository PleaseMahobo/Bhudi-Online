//go:build windows

package main

import (
	"fmt"
	"syscall"
)

var procSetProcessDpiAwarenessContext = user32.NewProc("SetProcessDpiAwarenessContext")

const dpiAwarenessContextPerMonitorAwareV2 = ^uintptr(3)

func init() {
	if r, _, _ := procSetProcessDpiAwarenessContext.Call(dpiAwarenessContextPerMonitorAwareV2); r != 0 {
		return
	}
	shcore := syscall.NewLazyDLL("shcore.dll")
	proc := shcore.NewProc("SetProcessDpiAwareness")
	if r, _, _ := proc.Call(2); r != 0 {
		return
	}
	fmt.Println("[remote-desktop] DPI awareness fallback unavailable")
}
