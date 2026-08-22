//go:build windows

package main

import (
	"os"
	"strings"

	"golang.org/x/sys/windows/registry"
	"github.com/google/uuid"
)

func machineGUID() string {
	if key, err := registry.OpenKey(registry.LOCAL_MACHINE, `SOFTWARE\Microsoft\Cryptography`, registry.QUERY_VALUE); err == nil {
		defer key.Close()
		if value, _, err := key.GetStringValue("MachineGuid"); err == nil && strings.TrimSpace(value) != "" {
			return strings.TrimSpace(value)
		}
	}

	return persistedMachineGUID()
}

func persistedMachineGUID() string {
	path := filepathJoin(dataDir(), "machine_guid")
	if data, err := os.ReadFile(path); err == nil {
		if value := strings.TrimSpace(string(data)); value != "" {
			return value
		}
	}
	value := uuid.NewString()
	_ = os.MkdirAll(dataDir(), 0755)
	_ = os.WriteFile(path, []byte(value), 0600)
	return value
}

func filepathJoin(parts ...string) string {
	if len(parts) == 0 {
		return ""
	}
	result := parts[0]
	for _, part := range parts[1:] {
		if result == "" {
			result = part
		} else {
			result = result + string(os.PathSeparator) + part
		}
	}
	return result
}
