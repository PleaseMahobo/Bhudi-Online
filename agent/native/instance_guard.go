package main

import (
	"fmt"
	"os"
	"strings"
)

func init() {
	if !isRuntimeCommand() {
		return
	}
	release, ok := acquireInstanceLock()
	if !ok {
		fmt.Fprintln(os.Stderr, "[bhudi-agent] another agent instance is already running")
		os.Exit(0)
	}
	// Keep the mutex handle alive for the lifetime of this process.
	_ = release
}

func isRuntimeCommand() bool {
	if len(os.Args) < 2 {
		return true
	}
	switch strings.ToLower(os.Args[1]) {
	case "run", "start", "service":
		return true
	default:
		return false
	}
}
