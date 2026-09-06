//go:build windows

package main

import (
	"encoding/json"
	"fmt"
	"os/exec"
	"strings"
	"time"
)

// patchUpdate is one missing or installed update reported to the portal.
type patchUpdate struct {
	Title       string `json:"title"`
	KB          string `json:"kb,omitempty"`
	Severity    string `json:"severity,omitempty"`
	SizeBytes   int64  `json:"size_bytes,omitempty"`
	IsInstalled bool   `json:"is_installed"`
	UpdateID    string `json:"update_id,omitempty"`
}

// runPatchScan queries Windows Update for missing software updates.
func runPatchScan(payload map[string]any) map[string]any {
	ps := `
$ErrorActionPreference = 'Stop'
try {
  $session = New-Object -ComObject Microsoft.Update.Session
  $searcher = $session.CreateUpdateSearcher()
  $result = $searcher.Search("IsInstalled=0 and Type='Software' and IsHidden=0")
  $list = @()
  foreach ($u in $result.Updates) {
    $kb = ''
    if ($u.KBArticleIDs -and $u.KBArticleIDs.Count -gt 0) { $kb = 'KB' + $u.KBArticleIDs.Item(0) }
    $sev = 'unspecified'
    try { $sev = [string]$u.MsrcSeverity } catch {}
    if (-not $sev) { $sev = 'unspecified' }
    $list += [PSCustomObject]@{
      title = $u.Title
      kb = $kb
      severity = $sev.ToLower()
      size_bytes = [int64]$u.MaxDownloadSize
      is_installed = $false
      update_id = $u.Identity.UpdateID
    }
  }
  $out = [PSCustomObject]@{ platform = 'windows'; scanned_at = (Get-Date).ToUniversalTime().ToString('o'); count = $list.Count; updates = $list }
  $out | ConvertTo-Json -Depth 6 -Compress
} catch {
  Write-Output ("{\"error\":\"" + ($_.Exception.Message -replace '"','') + "\"}")
  exit 1
}
`
	code, stdout, stderr := runPowerShell(ps, 180*time.Second)
	if code != 0 {
		return map[string]any{
			"exit_code": code,
			"stdout":    stdout,
			"stderr":    firstNonEmpty(stderr, "patch_scan failed"),
		}
	}
	return map[string]any{
		"exit_code": 0,
		"stdout":    strings.TrimSpace(stdout),
		"stderr":    stderr,
		"result":    tryParseJSON(stdout),
	}
}

// runPatchInstall installs missing Windows updates (optional KB filter via payload).
func runPatchInstall(payload map[string]any) map[string]any {
	kbFilter := firstString(payload, "kb", "kb_article", "update_id")
	maxUpdates := 20
	if v, ok := payload["max_updates"].(float64); ok && v > 0 {
		maxUpdates = int(v)
	}

	// Escape for embedding in PowerShell single-quoted string is limited; use env-style args.
	ps := fmt.Sprintf(`
$ErrorActionPreference = 'Stop'
$kbFilter = %q
$max = %d
try {
  $session = New-Object -ComObject Microsoft.Update.Session
  $searcher = $session.CreateUpdateSearcher()
  $result = $searcher.Search("IsInstalled=0 and Type='Software' and IsHidden=0")
  $toInstall = New-Object -ComObject Microsoft.Update.UpdateColl
  $selected = @()
  foreach ($u in $result.Updates) {
    if ($selected.Count -ge $max) { break }
    if (-not $u.EulaAccepted) { try { $u.AcceptEula() } catch {} }
    $kb = ''
    if ($u.KBArticleIDs -and $u.KBArticleIDs.Count -gt 0) { $kb = 'KB' + $u.KBArticleIDs.Item(0) }
    $id = $u.Identity.UpdateID
    if ($kbFilter -ne '' -and $kb -ne $kbFilter -and $id -ne $kbFilter -and $kbFilter -ne ('KB' + $kb.TrimStart('K','B'))) {
      continue
    }
    [void]$toInstall.Add($u)
    $selected += [PSCustomObject]@{ title = $u.Title; kb = $kb; update_id = $id }
  }
  if ($toInstall.Count -eq 0) {
    $empty = [PSCustomObject]@{ platform = 'windows'; installed = @(); message = 'no matching updates' }
    $empty | ConvertTo-Json -Compress
    exit 0
  }
  $downloader = $session.CreateUpdateDownloader()
  $downloader.Updates = $toInstall
  $dl = $downloader.Download()
  $installer = $session.CreateUpdateInstaller()
  $installer.Updates = $toInstall
  $inst = $installer.Install()
  $installed = @()
  for ($i = 0; $i -lt $toInstall.Count; $i++) {
    $ur = $inst.GetUpdateResult($i)
    $installed += [PSCustomObject]@{
      title = $toInstall.Item($i).Title
      result_code = [int]$ur.ResultCode
      reboot_required = [bool]$ur.RebootRequired
    }
  }
  $out = [PSCustomObject]@{
    platform = 'windows'
    download_result = [int]$dl.ResultCode
    install_result = [int]$inst.ResultCode
    reboot_required = [bool]$inst.RebootRequired
    installed = $installed
  }
  $out | ConvertTo-Json -Depth 6 -Compress
  if ([int]$inst.ResultCode -gt 2) { exit 1 }
  exit 0
} catch {
  Write-Output ("{\"error\":\"" + ($_.Exception.Message -replace '"','') + "\"}")
  exit 1
}
`, kbFilter, maxUpdates)
	code, stdout, stderr := runPowerShell(ps, 45*time.Minute)
	return map[string]any{
		"exit_code": code,
		"stdout":    strings.TrimSpace(stdout),
		"stderr":    stderr,
		"result":    tryParseJSON(stdout),
	}
}

func runPowerShell(script string, timeout time.Duration) (int, string, string) {
	cmd := exec.Command("powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script)
	var stdout, stderr strings.Builder
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr
	err := cmd.Start()
	if err != nil {
		return 1, "", err.Error()
	}
	done := make(chan error, 1)
	go func() { done <- cmd.Wait() }()
	select {
	case err := <-done:
		code := 0
		if err != nil {
			if ee, ok := err.(*exec.ExitError); ok {
				code = ee.ExitCode()
			} else {
				code = 1
				stderr.WriteString(err.Error())
			}
		}
		return code, stdout.String(), stderr.String()
	case <-time.After(timeout):
		_ = cmd.Process.Kill()
		return 1, stdout.String(), "patch operation timed out"
	}
}

func tryParseJSON(s string) any {
	s = strings.TrimSpace(s)
	if s == "" {
		return nil
	}
	var v any
	if json.Unmarshal([]byte(s), &v) == nil {
		return v
	}
	return nil
}

func firstNonEmpty(a, b string) string {
	if strings.TrimSpace(a) != "" {
		return a
	}
	return b
}


// firstString returns the first non-empty string value for the supplied keys.
func firstString(payload map[string]any, keys ...string) string {
	for _, key := range keys {
		if value, ok := payload[key]; ok {
			if s, ok := value.(string); ok && strings.TrimSpace(s) != "" {
				return strings.TrimSpace(s)
			}
		}
	}
	return ""
}
