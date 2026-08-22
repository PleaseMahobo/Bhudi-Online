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

// MarshalJSON injects the customer bootstrap and stable machine identity into
// the enrollment request without changing the existing agent request struct.
func (r enrollReq) MarshalJSON() ([]byte, error) {
	type plainEnrollReq enrollReq
	base, err := json.Marshal(plainEnrollReq(r))
	if err != nil {
		return nil, err
	}

	var value map[string]any
	if err := json.Unmarshal(base, &value); err != nil {
		return nil, err
	}

	if guid := strings.TrimSpace(machineGUID()); guid != "" {
		value["machine_guid"] = guid
	}

	if r.EnrollmentSecret == nil || strings.TrimSpace(*r.EnrollmentSecret) == "" {
		if b, err := os.ReadFile(filepath.Join(dataDir(), enrollmentSecretPathName)); err == nil {
			secret := strings.TrimSpace(string(b))
			if secret != "" {
				value["enrollment_secret"] = secret
				// Give the enrollment request time to complete, then remove the
				// one-time bootstrap from disk. The backend independently enforces
				// single-use semantics.
				go func(path string) {
					time.Sleep(30 * time.Second)
					_ = os.Remove(path)
				}(filepath.Join(dataDir(), enrollmentSecretPathName))
			}
		}
	}
	return json.Marshal(value)
}
