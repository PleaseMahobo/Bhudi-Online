//go:build !windows

package main

import (
	"encoding/json"
	"runtime"
)

func runPatchScan(payload map[string]any) map[string]any {
	out, _ := json.Marshal(map[string]any{
		"platform":   runtime.GOOS,
		"count":      0,
		"updates":    []any{},
		"message":    "patch_scan is fully implemented on Windows; use package-manager scripts on " + runtime.GOOS,
	})
	return map[string]any{
		"exit_code": 0,
		"stdout":    string(out),
		"stderr":    "",
		"result":    map[string]any{"platform": runtime.GOOS, "count": 0, "updates": []any{}},
	}
}

func runPatchInstall(payload map[string]any) map[string]any {
	return map[string]any{
		"exit_code": 1,
		"stdout":    "",
		"stderr":    "patch_install is fully implemented on Windows only",
	}
}
