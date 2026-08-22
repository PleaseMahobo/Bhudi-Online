package main

import (
    "fmt"
    "os"
    "path/filepath"
)

// installBundledAgent writes the exact native agent binary that was built with
// this installer. This prevents customer installers from silently downloading
// a different/stale agent release at install time.
func installBundledAgent(dest string) error {
    if len(bundledAgent) == 0 {
        return fmt.Errorf("bundled Bhudi agent payload is empty")
    }
    if err := os.MkdirAll(filepath.Dir(dest), 0755); err != nil {
        return err
    }
    return os.WriteFile(dest, bundledAgent, 0755)
}
