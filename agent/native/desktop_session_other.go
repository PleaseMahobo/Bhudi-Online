//go:build !windows

package main

// ensureInteractiveDesktop is a no-op on non-Windows platforms.
func ensureInteractiveDesktop() error {
	return nil
}

func desktopStatusNote() string {
	return "non-windows"
}

// desktopDiagnostics keeps remote-desktop status reporting portable across builds.
func desktopDiagnostics() map[string]any {
	return map[string]any{
		"platform": "non-windows",
		"desktop_ready": false,
	}
}

func activeConsoleSessionID() uint32 {
	return 0
}
