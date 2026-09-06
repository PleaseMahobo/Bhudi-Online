package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"time"
)

const defaultServerURL = "https://bhudi-online-production.up.railway.app"

type runConfig struct {
	Server   string
	Interval int
}

type identity struct {
	AgentID    string `json:"agent_id"`
	AgentToken string `json:"agent_token"`
}

type enrollReq struct {
	Hostname         string  `json:"hostname"`
	AgentVersion     string  `json:"agent_version"`
	Platform         string  `json:"platform"`
	EnrollmentSecret *string `json:"enrollment_secret,omitempty"`
}

type enrollResp struct {
	AgentID           string `json:"agent_id"`
	AgentToken        string `json:"agent_token"`
	HeartbeatInterval int    `json:"heartbeat_interval"`
	PollInterval      int    `json:"poll_interval"`
}

type heartbeatReq struct {
	AgentID       string   `json:"agent_id"`
	AgentToken    string   `json:"agent_token"`
	Status        string   `json:"status"`
	CPUPercent    *float64 `json:"cpu_percent"`
	MemoryPercent *float64 `json:"memory_percent"`
	DiskPercent   *float64 `json:"disk_percent"`
	IPAddress     *string  `json:"ip_address"`
	Hostname      *string  `json:"hostname"`
}

type commandItem struct {
	CommandID   string         `json:"command_id"`
	Command     string         `json:"command"`
	Shell       bool           `json:"shell"`
	CommandType string         `json:"command_type"`
	Payload     map[string]any `json:"payload"`
}

func runAgent(cfg runConfig) {
	if cfg.Server == "" {
		cfg.Server = defaultServerURL
	}
	if cfg.Interval < 5 {
		cfg.Interval = 5
	}
	fmt.Printf("[bhudi-agent] version=%s server=%s os=%s/%s\n", agentVersion, cfg.Server, runtime.GOOS, runtime.GOARCH)

	ident, err := loadOrEnroll(cfg.Server)
	if err != nil {
		fatal(fmt.Errorf("enroll: %w", err))
	}
	fmt.Printf("[bhudi-agent] agent_id=%s host=%s\n", ident.AgentID, hostname())

	client := &http.Client{Timeout: 30 * time.Second}
	for {
		if err := cycle(client, cfg.Server, &ident); err != nil {
			fmt.Println("[error]", err)
			// A heartbeat can succeed while an optional command poll fails. Do not
			// destroy a healthy enrollment or attempt bootstrap re-enrollment for a
			// poll-only 401. Re-enrollment is reserved for failures that explicitly
			// identify the stored agent credentials as invalid.
			if isInvalidAgentCredential(err) {
				secret := enrollmentSecret()
				if secret == "" {
					fmt.Println("[bhudi-agent] agent credentials invalid — keeping identity (no enrollment secret)")
				} else {
					fmt.Println("[bhudi-agent] agent credentials invalid — re-enrolling with bootstrap secret…")
					clearIdentity()
					newID, e2 := enroll(cfg.Server)
					if e2 != nil {
						fmt.Println("[error] re-enroll:", e2)
					} else {
						ident = newID
						fmt.Printf("[bhudi-agent] re-enrolled agent_id=%s\n", ident.AgentID)
					}
				}
			}
		}
		time.Sleep(time.Duration(cfg.Interval) * time.Second)
	}
}

func cycle(client *http.Client, server string, ident *identity) error {
	if err := sendHeartbeat(client, server, *ident); err != nil {
		return err
	}
	// Commands are polled only through the agent-authenticated runtime endpoint.
	// Do not call the legacy /api/v1/agents/... enterprise routes; they are not
	// agent polling endpoints and produced repeated HTTP 405 noise.
	cmds, err := pollCommands(client, server, *ident)
	if err != nil {
		return err
	}
	for _, c := range cmds {
		code, out, errOut := runShell(c.Command, c.Shell)
		_ = postResult(client, server, *ident, c.CommandID, code, out, errOut)
	}
	return nil
}

func str(v any) string {
	if v == nil {
		return ""
	}
	switch t := v.(type) {
	case string:
		return t
	default:
		return fmt.Sprint(t)
	}
}

func executeEnterpriseCommand(server string, ident identity, cmd map[string]any) map[string]any {
	ctype := strings.ToLower(str(cmd["command_type"]))
	payload, _ := cmd["payload"].(map[string]any)
	if payload == nil {
		payload = map[string]any{}
	}
	switch ctype {
	case "patch_scan":
		return runPatchScan(payload)
	case "patch_install":
		return runPatchInstall(payload)
	default:
		command := str(cmd["command"])
		if command == "" {
			command = str(payload["command"])
		}
		shell := true
		if v, ok := cmd["shell"].(bool); ok {
			shell = v
		}
		code, out, errOut := runShell(command, shell)
		return map[string]any{"exit_code": code, "stdout": out, "stderr": errOut}
	}
}

func loadOrEnroll(server string) (identity, error) {
	path := identityPath()
	secret := enrollmentSecret()
	if data, err := os.ReadFile(path); err == nil {
		var id identity
		if json.Unmarshal(data, &id) == nil && id.AgentID != "" && id.AgentToken != "" {
			// A tenant-bound installer credential is authoritative. Re-enroll so
			// legacy identities created before tenant binding are migrated instead
			// of silently continuing to heartbeat outside the tenant portal.
			if secret == "" {
				return id, nil
			}
			fmt.Println("[bhudi-agent] tenant enrollment credential detected — migrating existing agent identity")
			clearIdentity()
			return enroll(server)
		}
	}
	return enroll(server)
}

func clearIdentity() {
	_ = os.Remove(identityPath())
}

func enrollmentSecret() string {
	secret := strings.TrimSpace(os.Getenv("BHUDI_ENROLLMENT_TOKEN"))
	if secret == "" {
		if b, err := os.ReadFile(filepath.Join(dataDir(), enrollmentSecretPathName)); err == nil {
			secret = strings.TrimSpace(string(b))
		}
	}
	return secret
}

func isInvalidAgentCredential(err error) bool {
	if err == nil {
		return false
	}
	// Only the runtime agent-authentication failure proves the stored identity
	// is bad. Generic HTTP 401 responses can come from optional portal routes.
	s := err.Error()
	return strings.Contains(s, "Invalid agent credentials")
}

func enroll(server string) (identity, error) {
	body := enrollReq{
		Hostname:     hostname(),
		AgentVersion: agentVersion,
		Platform:     runtime.GOOS + "/" + runtime.GOARCH + " " + runtime.Version(),
	}
	// The customer-specific installer supplies the bootstrap credential via
	// BHUDI_ENROLLMENT_TOKEN. Include it in the enrollment request; previously
	// the native agent read the variable only during re-enrollment and silently
	// omitted it from the initial enrollment payload.
	secret := strings.TrimSpace(os.Getenv("BHUDI_ENROLLMENT_TOKEN"))
	if secret == "" {
		if b, err := os.ReadFile(filepath.Join(dataDir(), enrollmentSecretPathName)); err == nil {
			secret = strings.TrimSpace(string(b))
		}
	}
	if secret != "" {
		body.EnrollmentSecret = &secret
	}
	var resp enrollResp
	if err := postJSON(server+"/api/v1/runtime/enroll", body, &resp); err != nil {
		return identity{}, err
	}
	id := identity{AgentID: resp.AgentID, AgentToken: resp.AgentToken}
	_ = os.MkdirAll(filepath.Dir(identityPath()), 0755)
	data, _ := json.MarshalIndent(id, "", "  ")
	if err := os.WriteFile(identityPath(), data, 0600); err != nil {
		return identity{}, fmt.Errorf("write agent identity: %w", err)
	}
	if err := writeConfig(server); err != nil {
		return identity{}, fmt.Errorf("write agent config: %w", err)
	}
	return id, nil
}

func sendHeartbeat(client *http.Client, server string, ident identity) error {
	host := hostname()
	ip := localIP()
	cpu, mem, disk := sampleMetrics()
	req := heartbeatReq{
		AgentID:       ident.AgentID,
		AgentToken:    ident.AgentToken,
		Status:        "online",
		CPUPercent:    cpu,
		MemoryPercent: mem,
		DiskPercent:   disk,
		IPAddress:     &ip,
		Hostname:      &host,
	}
	var raw map[string]any
	if err := postJSONClient(client, server+"/api/v1/runtime/heartbeat", req, &raw); err != nil {
		return err
	}
	pending, _ := raw["pending_commands"].(float64)
	fmt.Printf("[heartbeat] ok pending=%.0f\n", pending)
	return nil
}

func pollCommands(client *http.Client, server string, ident identity) ([]commandItem, error) {
	// Agent polling uses the agent-authenticated pending endpoint. The generic
	// /commands endpoint is a portal/history endpoint and may require a user
	// session, which caused a healthy agent to receive a misleading HTTP 401.
	url := fmt.Sprintf("%s/api/v1/runtime/agents/%s/commands/pending?agent_token=%s", server, ident.AgentID, ident.AgentToken)
	res, err := client.Get(url)
	if err != nil {
		return nil, err
	}
	defer res.Body.Close()
	b, _ := io.ReadAll(res.Body)
	if res.StatusCode >= 300 {
		return nil, fmt.Errorf("poll HTTP %d: %s", res.StatusCode, string(b))
	}
	var out struct {
		Commands []commandItem `json:"commands"`
	}
	if err := json.Unmarshal(b, &out); err != nil {
		return nil, err
	}
	return out.Commands, nil
}

func postResult(client *http.Client, server string, ident identity, commandID string, exitCode int, stdout, stderr string) error {
	url := fmt.Sprintf("%s/api/v1/runtime/agents/%s/commands/%s/result?agent_token=%s", server, ident.AgentID, commandID, ident.AgentToken)
	body := map[string]any{"exit_code": exitCode, "stdout": stdout, "stderr": stderr}
	b, _ := json.Marshal(body)
	res, err := client.Post(url, "application/json", bytes.NewReader(b))
	if err != nil {
		return err
	}
	defer res.Body.Close()
	return nil
}

func runShell(command string, shell bool) (int, string, string) {
	var cmd *exec.Cmd
	if runtime.GOOS == "windows" {
		cmd = exec.Command("cmd", "/C", command)
	} else if shell {
		cmd = exec.Command("bash", "-lc", command)
	} else {
		cmd = exec.Command("sh", "-c", command)
	}
	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr
	err := cmd.Run()
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
}

func postJSON(url string, in any, out any) error {
	return postJSONClient(&http.Client{Timeout: 30 * time.Second}, url, in, out)
}

func postJSONClient(client *http.Client, url string, in any, out any) error {
	b, err := json.Marshal(in)
	if err != nil {
		return err
	}
	res, err := client.Post(url, "application/json", bytes.NewReader(b))
	if err != nil {
		return err
	}
	defer res.Body.Close()
	body, _ := io.ReadAll(res.Body)
	if res.StatusCode >= 300 {
		return fmt.Errorf("HTTP %d: %s", res.StatusCode, string(body))
	}
	if out == nil || len(body) == 0 {
		return nil
	}
	return json.Unmarshal(body, out)
}

func hostname() string {
	if h := os.Getenv("BHUDI_HOSTNAME"); h != "" {
		return h
	}
	h, err := os.Hostname()
	if err != nil {
		return "unknown"
	}
	return h
}

func localIP() string {
	addrs, err := net.InterfaceAddrs()
	if err != nil {
		return ""
	}
	for _, a := range addrs {
		if ipnet, ok := a.(*net.IPNet); ok && !ipnet.IP.IsLoopback() && ipnet.IP.To4() != nil {
			return ipnet.IP.String()
		}
	}
	return ""
}

func dataDir() string {
	if runtime.GOOS == "windows" {
		base := os.Getenv("ProgramData")
		if base == "" {
			base = os.Getenv("LOCALAPPDATA")
		}
		if base == "" {
			base = "."
		}
		return filepath.Join(base, "Bhudi", "Agent")
	}
	if runtime.GOOS == "darwin" {
		return filepath.Join(os.Getenv("HOME"), "Library", "Application Support", "Bhudi", "Agent")
	}
	if xdg := os.Getenv("XDG_STATE_HOME"); xdg != "" {
		return filepath.Join(xdg, "bhudi-agent")
	}
	home, _ := os.UserHomeDir()
	return filepath.Join(home, ".local", "state", "bhudi-agent")
}

func identityPath() string {
	return filepath.Join(dataDir(), "agent_identity.json")
}

func writeConfig(server string) error {
	_ = os.MkdirAll(dataDir(), 0755)
	cfg := map[string]any{"server_url": server, "agent_version": agentVersion}
	b, _ := json.MarshalIndent(cfg, "", "  ")
	return os.WriteFile(filepath.Join(dataDir(), "agent_config.json"), b, 0644)
}
