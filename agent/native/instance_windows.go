//go:build windows

package main

import (
	"syscall"
	"unsafe"
)

var (
	modKernelInstance = syscall.NewLazyDLL("kernel32.dll")
	procCreateMutexW  = modKernelInstance.NewProc("CreateMutexW")
	procCloseHandleW  = modKernelInstance.NewProc("CloseHandle")
)

func acquireInstanceLock() (release func(), ok bool) {
	name, _ := syscall.UTF16PtrFromString("Local\\BhudiAgentSingleton")
	h, _, err := procCreateMutexW.Call(0, 0, uintptr(unsafe.Pointer(name)))
	if h == 0 {
		return func() {}, false
	}
	if errno, ok := err.(syscall.Errno); ok && errno == 183 {
		procCloseHandleW.Call(h)
		return func() {}, false
	}
	return func() { procCloseHandleW.Call(h) }, true
}
