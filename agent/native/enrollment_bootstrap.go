package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"time"
)

const enrollmentSecretPathName = "enrollment_secret"

// The native install command itself remains backward compatible. The
// customer-specific setup process supplies BHUDI_ENROLLMENT_TOKEN in its
// environment; init persists it before the service is registered.
func init() {
	secret := strings.TrimSpace(os.Getenv("BHUDI_ENROLLMENT_TOKEN"))
	if secret == "" {
		return
	}
	if err := os.MkdirAll(dataDir(), 0755); err != nil {
		return
	}
	_ = os.WriteFile(filepath.Join(dataDir(), enrollmentSecretPathName), []byte(secret), 0600)
}

// MarshalJSON transparently injects the customer bootstrap into the existing
// enrollment request. This lets the published native agent remain compatible
// with its existing install command while customer installers get secure,
// tenant-bound enrollment automatically.
func (r enrollReq) MarshalJSON() ([]byte, error) {
	type plainEnrollReq enrollReq
	value := plainEnrollReq(r)
	if value.EnrollmentSecret == nil || strings.TrimSpace(*value.EnrollmentSecret) == "" {
		if b, err := os.ReadFile(filepath.Join(dataDir(), enrollmentSecretPathName)); err == nil {
			secret := strings.TrimSpace(string(b))
			if secret != "" {
				value.EnrollmentSecret = &secret
				// Give the enrollment request time to complete, then remove the
				// one-time bootstrap from disk. The backend independently enforces
				// single-use semantics, so the token cannot be reused successfully.
				go func(path string) {
					time.Sleep(30 * time.Second)
					_ = os.Remove(path)
				}(filepath.Join(dataDir(), enrollmentSecretPathName))
			}
		}
	}
	return json.Marshal(value)
}
