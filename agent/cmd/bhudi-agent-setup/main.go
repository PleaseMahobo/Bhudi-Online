package main

import (
	"encoding/binary"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"time"
)

const (
	defaultServer = "https://bhudi-online-production.up.railway.app"
	supportURL = "https://github.com/PleaseMahobo/Bhudi-Online/releases/download/agent-native-latest/bhudi-support.exe"
	magic = "BHUDI_BOOTSTRAP_V1"
	agentVersion = "2.1.0"
)

type bootstrap struct { ServerURL string `json:"server_url"`; EnrollmentToken string `json:"enrollment_token"` }
type installedIdentity struct { AgentID string `json:"agent_id"`; AgentToken string `json:"agent_token"` }
type runConfig struct { Server string; Interval int }

func main() {
	if runtime.GOOS == "windows" && len(os.Args) < 2 { ensureElevated(); runInstallerGUI(); return }
	ensureElevated()
	cmd := ""; if len(os.Args) > 1 { cmd = strings.ToLower(os.Args[1]) }
	switch cmd {
	case "install-worker", "install": if err := runInstallWorkflow(); err != nil { fatal(err) }
	case "enroll": cfg := readRunConfig(os.Args[2:]); if err := runNativeEnroll(cfg.Server); err != nil { fatal(err) }
	case "upgrade": cfg := readRunConfig(os.Args[2:]); logInstall("upgrade start version=%s server=%s", agentVersion, cfg.Server); if err := upgradeAgent(cfg.Server); err != nil { fatal(err) }
	case "uninstall": if err := uninstallService(); err != nil { fatal(err) }
	case "version", "-v", "--version": fmt.Println("bhudi-agent-setup", agentVersion)
	case "help", "-h", "--help": fmt.Println("Bhudi Agent Setup — double-click for the graphical installer")
	default: fatal(fmt.Errorf("unknown command %q", cmd))
	}
}

func readRunConfig(args []string) runConfig { server := envOr("BHUDI_SERVER_URL", defaultServer); for i := 0; i < len(args)-1; i++ { if args[i] == "-server" { server = args[i+1] } }; return runConfig{Server: strings.TrimRight(server, "/"), Interval: 10} }
func runNativeEnroll(server string) error { return fmt.Errorf("enrollment must be performed by the bundled native agent") }
func upgradeAgent(server string) error { return fmt.Errorf("upgrade must be performed by the installed native agent: %s", server) }
func uninstallService() error { if runtime.GOOS != "windows" { return fmt.Errorf("uninstall is supported on Windows only") }; _ = exec.Command("sc", "stop", "BhudiAgent").Run(); _ = exec.Command("sc", "delete", "BhudiAgent").Run(); _ = exec.Command("schtasks", "/Delete", "/TN", "BhudiAgent", "/F").Run(); _ = exec.Command("schtasks", "/Delete", "/TN", "BhudiAgentWatchdog", "/F").Run(); return nil }
func logInstall(format string, args ...interface{}) { fmt.Printf(format+"\n", args...) }

func runInstallWorkflow() error {
	boot, err := readBootstrap(); if err != nil { return fmt.Errorf("this is not a customer-specific Bhudi installer: %w", err) }
	server := strings.TrimRight(strings.TrimSpace(boot.ServerURL), "/"); if server == "" { server = defaultServer }
	if strings.TrimSpace(boot.EnrollmentToken) == "" { return fmt.Errorf("customer enrollment information is missing") }; if runtime.GOOS != "windows" { return fmt.Errorf("this installer is for Windows") }
	tmp, err := os.MkdirTemp("", "bhudi-setup-*"); if err != nil { return err }; defer os.RemoveAll(tmp)
	agentPath := filepath.Join(tmp, "bhudi-agent.exe"); if err := installBundledAgent(agentPath); err != nil { return fmt.Errorf("bundled agent: %w", err) }
	identity := filepath.Join(os.Getenv("ProgramData"), "Bhudi", "Agent", "agent_identity.json")
	if !hasValidIdentity(identity) { cmd := exec.Command(agentPath, "enroll", "-server", server); cmd.Env = append(os.Environ(), "BHUDI_ENROLLMENT_TOKEN="+boot.EnrollmentToken); cmd.Stdout = os.Stdout; cmd.Stderr = os.Stderr; if err := cmd.Run(); err != nil { return fmt.Errorf("agent enrollment failed: %w", err) }; if !hasValidIdentity(identity) { return fmt.Errorf("enrollment completed without creating agent_identity.json") } }
	cmd := exec.Command(agentPath, "install", "-server", server); cmd.Stdout = os.Stdout; cmd.Stderr = os.Stderr; if err := cmd.Run(); err != nil { return fmt.Errorf("agent installation failed: %w", err) }
	supportDir := filepath.Join(os.Getenv("ProgramFiles"), "Bhudi", "Support"); if supportDir == "" { supportDir = filepath.Join(os.Getenv("ProgramData"), "Bhudi", "Support") }; if err := os.MkdirAll(supportDir, 0755); err != nil { return err }
	supportPath := filepath.Join(supportDir, "bhudi-support.exe"); if err := download(supportURL, supportPath); err != nil { return fmt.Errorf("support-client download: %w", err) }; if !hasValidIdentity(identity) { return fmt.Errorf("agent identity disappeared after service installation") }; if err := startSupportClient(supportPath); err != nil { return fmt.Errorf("support-client start: %w", err) }; return nil
}
func installBundledAgent(dest string) error { if len(bundledAgent) == 0 { return fmt.Errorf("bundled Bhudi agent payload is empty") }; return os.WriteFile(dest, bundledAgent, 0755) }
func hasValidIdentity(path string) bool { data, err := os.ReadFile(path); if err != nil { return false }; var id installedIdentity; return json.Unmarshal(data, &id) == nil && strings.TrimSpace(id.AgentID) != "" && strings.TrimSpace(id.AgentToken) != "" }
func startSupportClient(path string) error { cmd := exec.Command(path); if err := cmd.Start(); err != nil { return err }; _ = exec.Command("reg.exe", "ADD", `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`, "BhudiSupport", "/REG_SZ", path, "/F").Run(); return nil }
func readBootstrap() (bootstrap, error) { exe, err := os.Executable(); if err != nil { return bootstrap{}, err }; f, err := os.Open(exe); if err != nil { return bootstrap{}, err }; defer f.Close(); stat, err := f.Stat(); if err != nil { return bootstrap{}, err }; footerSize := int64(len(magic)+8); if stat.Size() < footerSize { return bootstrap{}, fmt.Errorf("customer bootstrap payload not found") }; if _, err = f.Seek(-footerSize, io.SeekEnd); err != nil { return bootstrap{}, err }; footer := make([]byte, footerSize); if _, err = io.ReadFull(f, footer); err != nil { return bootstrap{}, err }; if string(footer[8:]) != magic { return bootstrap{}, fmt.Errorf("invalid customer bootstrap footer") }; length := binary.LittleEndian.Uint64(footer[:8]); if length == 0 || length > 1024*1024 || int64(length)+footerSize > stat.Size() { return bootstrap{}, fmt.Errorf("invalid customer bootstrap length") }; if _, err = f.Seek(-(footerSize+int64(length)), io.SeekEnd); err != nil { return bootstrap{}, err }; payload := make([]byte, length); if _, err = io.ReadFull(f, payload); err != nil { return bootstrap{}, err }; var boot bootstrap; if err = json.Unmarshal(payload, &boot); err != nil { return bootstrap{}, fmt.Errorf("invalid customer bootstrap payload") }; return boot, nil }
func download(url, dest string) error { client := &http.Client{Timeout: 2 * time.Minute}; resp, err := client.Get(url); if err != nil { return err }; defer resp.Body.Close(); if resp.StatusCode != http.StatusOK { return fmt.Errorf("HTTP %d", resp.StatusCode) }; f, err := os.Create(dest); if err != nil { return err }; defer f.Close(); _, err = io.Copy(f, resp.Body); return err }
func fatal(err error) { fmt.Fprintln(os.Stderr, "ERROR:", err); os.Exit(1) }
func envOr(k, def string) string { if v := strings.TrimSpace(os.Getenv(k)); v != "" { return v }; return def }
