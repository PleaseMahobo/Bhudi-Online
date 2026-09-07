//go:build !windows

package main

// ensureInteractiveDesktop is a no-op on non-Windows platforms.
func ensureInteractiveDesktop() error {
	return nil
}

func desktopStatusNote() string {
	return "non-windows"
}

func activeConsoleSessionID() uint32 {
	return 0
}
