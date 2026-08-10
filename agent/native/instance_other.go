//go:build !windows

package main

import (
	"os"
	"path/filepath"
	"strconv"
	"syscall"
)

func acquireInstanceLock() (release func(), ok bool) {
	_ = os.MkdirAll(dataDir(), 0755)
	lock := filepath.Join(dataDir(), "agent.lock")
	f, err := os.OpenFile(lock, os.O_CREATE|os.O_RDWR, 0644)
	if err != nil {
		return func() {}, true
	}
	if err := syscall.Flock(int(f.Fd()), syscall.LOCK_EX|syscall.LOCK_NB); err != nil {
		_ = f.Close()
		return func() {}, false
	}
	_, _ = f.WriteString(strconv.Itoa(os.Getpid()))
	return func() {
		_ = syscall.Flock(int(f.Fd()), syscall.LOCK_UN)
		_ = f.Close()
	}, true
}
