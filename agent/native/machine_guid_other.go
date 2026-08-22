//go:build !windows

package main

import (
	"os"
	"path/filepath"
	"strings"

	"github.com/google/uuid"
)

func machineGUID() string {
	path := filepath.Join(dataDir(), "machine_guid")
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
