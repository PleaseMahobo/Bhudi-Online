//go:build !windows

package main

// ensureElevated is a no-op for CI builds that compile the installer package
// on non-Windows runners. The production installer uses elevate_windows.go.
func ensureElevated() {}
