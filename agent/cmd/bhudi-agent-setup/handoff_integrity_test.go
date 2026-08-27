//go:build release

package main

import (
	"bytes"
	"crypto/sha256"
	"os"
	"testing"
)

// TestBundledAgentMatchesStagedBinary proves that the customer installer embeds
// exactly the native agent staged by CI. It compares bytes, not just metadata.
func TestBundledAgentMatchesStagedBinary(t *testing.T) {
	staged, err := os.ReadFile("bhudi-agent.exe")
	if err != nil {
		t.Fatalf("read staged agent: %v", err)
	}
	if len(staged) == 0 {
		t.Fatal("staged agent is empty")
	}
	if !bytes.Equal(staged, bundledAgent) {
		stagedHash := sha256.Sum256(staged)
		embeddedHash := sha256.Sum256(bundledAgent)
		t.Fatalf("embedded agent differs from staged agent: staged=%x embedded=%x", stagedHash, embeddedHash)
	}
}

func TestBootstrapContract(t *testing.T) {
	if magic != "BHUDI_BOOTSTRAP_V1" {
		t.Fatalf("unexpected bootstrap magic: %q", magic)
	}
}
