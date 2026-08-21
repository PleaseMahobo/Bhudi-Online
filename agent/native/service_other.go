//go:build !windows

package main

import "fmt"

func runWindowsService(_ string) error {
	return fmt.Errorf("Windows Service mode is only supported on Windows")
}

func isWindowsServiceProcess() bool {
	return false
}
