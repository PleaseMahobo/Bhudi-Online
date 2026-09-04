package main

import (
	"os"
	"path/filepath"
	"runtime"
	"time"

	"github.com/shirou/gopsutil/v3/cpu"
	"github.com/shirou/gopsutil/v3/disk"
	"github.com/shirou/gopsutil/v3/mem"
)

// sampleMetrics returns CPU, memory, and primary disk usage percentages.
func sampleMetrics() (cpuPct, memPct, diskPct *float64) {
	if vals, err := cpu.Percent(400*time.Millisecond, false); err == nil && len(vals) > 0 {
		v := vals[0]
		cpuPct = &v
	}
	if vm, err := mem.VirtualMemory(); err == nil {
		v := vm.UsedPercent
		memPct = &v
	}
	root := "/"
	if runtime.GOOS == "windows" {
		root = os.Getenv("SystemDrive")
		if root == "" {
			root = "C:"
		}
		if len(root) == 2 && root[1] == ':' {
			root = root + `\`
		}
	}
	if du, err := disk.Usage(filepath.Clean(root)); err == nil {
		v := du.UsedPercent
		diskPct = &v
	}
	return cpuPct, memPct, diskPct
}
