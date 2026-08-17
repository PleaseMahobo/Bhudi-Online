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

const defaultServerURL = "https://generous-presence-production-b237.up.railway.app"

type runConfig struct {
	Server         string
	Interval       int
	EnrollmentToken string
}

type identity struct {
	AgentID    string `json:"agent_id"`
	AgentToken string `json:"agent_token"`
}

type enrollReq struct {
	Hostname      string  `json:"hostname"`
	AgentVersion  string  `json:"agent_version"`
	Platform      string  `json:"platform"`
	EnrollmentSecret *string `json:"enrollment_secret,omitempty"`
}

type enrollResp struct {
	AgentID          string `json:"agent_id"`
	AgentToken       string `json:"agent_token"`
	HeartbeatInterval int   `json:"heartbeat_interval"`
	PollInterval      int   `json:"poll_interval"`
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
	ident, err := loadOrEnroll(cfg.Server, cfg.EnrollmentToken)
	if err != nil {
		fatal(fmt.Errorf("enroll: %w", err))
	}
	fmt.Printf("[bhudi-agent] agent_id=%s host=%s\n", ident.AgentID, hostname())

	client := &http.Client{Timeout: 30 * time.Second}
	for {
		if err := cycle(client, cfg.Server, &ident); err != nil {
			fmt.Println("[error]", err)
			// Enrollment credentials are single-use bootstrap credentials and are
			// intentionally removed after successful enrollment. Do not attempt to
			// re-enroll with an empty token after a transient/auth failure. The
			// service remains alive and continues retrying with the issued identity.
			if isAuthError(err) {
				fmt.Println("[error] agent authentication failed; reinstall or issue a new customer enrollment token to replace the identity")
			}
		}
		time.Sleep(time.Duration(cfg.Interval) * time.Second)
	}
}

func cycle(client *http.Client, server string, ident *identity) error {
	if err := sendHeartbeat(client, server, *ident); err != nil {
		return err
	}

	for _, cmd := range pollEnterpriseCommands(client, server, *ident) {
		id := firstString(cmd, "command_id", "id")
		if id == "" {
			continue
		}
		_ = markEnterpriseSent(client, server, *ident, id)
		result := executeEnterpriseCommand(server, *ident, cmd)
		_ = postEnterpriseResult(client, server, *ident, id, result)
	}

	cmds, err := pollCommands(client, server, *ident)
	if err != nil {
		return err
	}
	for _, c := range cmds {
		if c.CommandType == "remote.desktop.start" || c.CommandType == "remote.desktop.webrtc" || c.CommandType == "remote.terminal.start" {
			m := map[string]any{"command_id": c.CommandID, "command_type": c.CommandType, "payload": c.Payload}
			r := executeEnterpriseCommand(server, *ident, m)
			code := intValue(r["exit_code"])
			out, _ := r["stdout"].(string)
			er, _ := r["stderr"].(string)
			_ = postResult(client, server, *ident, c.CommandID, code, out, er)
			continue
		}
		code, out, er := runCommand(c.Command, c.Shell)
		_ = postResult(client, server, *ident, c.CommandID, code, out, er)
	}
	return nil
}

func executeEnterpriseCommand(server string, ident identity, cmd map[string]any) map[string]any {
	typ := firstString(cmd, "command_type")
	payload, _ := cmd["payload"].(map[string]any)
	if payload == nil {
		payload = map[string]any{}
	}

	switch typ {
	case "remote.desktop.start":
		return startRemoteDesktop(server, ident.AgentID, cmd)
	case "remote.desktop.webrtc":
		return startRemoteDesktopWebRTC(server, ident.AgentID, cmd)
	case "remote.terminal.start":
		interactive := true
		if v, ok := payload["interactive"].(bool); ok {
			interactive = v
		}
		if interactive {
			return startRemoteTerminal(server, ident.AgentID, cmd)
		}
		fallthrough
	case "remote.cmd", "remote.powershell", "remote_script", "remote_powershell":
		shellCmd := firstString(payload, "command", "script")
		if shellCmd == "" {
			return map[string]any{"exit_code": 1, "stderr": "no command"}
		}
		code, out, er := runCommand(shellCmd, true)
		return map[string]any{"exit_code": code, "stdout": out, "stderr": er}
	case "remote.reboot":
		command := "sudo reboot"
		if runtime.GOOS == "windows" {
			command = "shutdown /r /t 5"
		}
		code, out, er := runCommand(command, true)
		return map[string]any{"exit_code": code, "stdout": out, "stderr": er}
	default:
		if shellCmd := firstString(payload, "command", "script"); shellCmd != "" {
			code, out, er := runCommand(shellCmd, true)
			return map[string]any{"exit_code": code, "stdout": out, "stderr": er}
		}
		return map[string]any{"exit_code": 1, "stderr": "unsupported command_type: " + typ}
	}
}

func pollEnterpriseCommands(client *http.Client, server string, ident identity) []map[string]any {
	url := server + "/api/v1/agent/" + ident.AgentID + "/commands"
	req, err := http.NewRequest(http.MethodGet, url, nil)
	if err != nil {
		return nil
	}
	res, err := client.Do(req)
	if err != nil {
		return nil
	}
	defer res.Body.Close()
	if res.StatusCode == http.StatusNotFound || res.StatusCode >= 300 {
		return nil
	}
	b, _ := io.ReadAll(res.Body)
	var list []map[string]any
	if json.Unmarshal(b, &list) == nil {
		return list
	}
	var wrapper struct {
		Commands []map[string]any `json:"commands"`
	}
	if json.Unmarshal(b, &wrapper) == nil {
		return wrapper.Commands
	}
	return nil
}

func markEnterpriseSent(client *http.Client, server string, ident identity, id string) error {
	if id == "" {
		return nil
	}
	res, err := client.Post(server+"/api/v1/agent/"+ident.AgentID+"/commands/"+id+"/sent", "application/json", nil)
	if err != nil {
		return err
	}
	defer res.Body.Close()
	return nil
}

func postEnterpriseResult(client *http.Client, server string, ident identity, id string, result map[string]any) error {
	if id == "" {
		return nil
	}
	code := intValue(result["exit_code"])
	ep := "failed"
	var body any
	if code == 0 {
		ep = "completed"
		body = result
	} else {
		body = map[string]any{"message": firstString(result, "stderr", "stdout")}
	}
	return postJSONClient(client, server+"/api/v1/agent/"+ident.AgentID+"/commands/"+id+"/"+ep, body, nil)
}

func firstString(m map[string]any, keys ...string) string {
	for _, k := range keys {
		if v := m[k]; v != nil {
			s := strings.TrimSpace(fmt.Sprint(v))
			if s != "" && s != "<nil>" {
				return s
			}
		}
	}
	return ""
}

func intValue(v any) int {
	switch n := v.(type) {
	case int:
		return n
	case float64:
		return int(n)
	default:
		return 0
	}
}

func loadOrEnroll(server, token string) (identity, error) {
	path := identityPath()
	if data, err := os.ReadFile(path); err == nil {
		var id identity
		if json.Unmarshal(data, &id) == nil && id.AgentID != "" && id.AgentToken != "" {
			return id, nil
		}
	}
	if token == "" {
		token = loadBootstrapToken()
	}
	return enroll(server, token)
}

func loadBootstrapToken() string {
	p := enrollmentTokenPath()
	b, err := os.ReadFile(p)
	if err != nil {
		return ""
	}
	return strings.TrimSpace(string(b))
}

func isAuthError(err error) bool {
	if err == nil {
		return false
	}
	s := err.Error()
	return strings.Contains(s, "401") || strings.Contains(s, "Invalid agent credentials") || strings.Contains(s, "Authentication failed")
}

func enroll(server, token string) (identity, error) {
	body := enrollReq{
		Hostname:     hostname(),
		AgentVersion: agentVersion,
		Platform:     runtime.GOOS + "/" + runtime.GOARCH + " " + runtime.Version(),
	}
	if token == "" {
		return identity{}, fmt.Errorf("no enrollment token available; generate a customer installer token in the portal")
	}
	body.EnrollmentSecret = &token

	var resp enrollResp
	if err := postJSON(server+"/api/v1/runtime/enroll", body, &resp); err != nil {
		return identity{}, err
	}
	id := identity{AgentID: resp.AgentID, AgentToken: resp.AgentToken}
	_ = os.MkdirAll(filepath.Dir(identityPath()), 0755)
	data, _ := json.MarshalIndent(id, "", "  ")
	_ = os.WriteFile(identityPath(), data, 0600)
	_ = os.Remove(enrollmentTokenPath())
	_ = writeConfig(server)
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
		Hostname:      &host,
	}
	if ip != "" {
		req.IPAddress = &ip
	}
	var raw map[string]any
	if err := postJSONClient(client, server+"/api/v1/runtime/heartbeat", req, &raw); err != nil {
		return err
	}
	fmt.Printf("[heartbeat] ok pending=%.0f\n", rawFloat(raw["pending_commands"]))
	return nil
}

func rawFloat(v any) float64 {
	if n, ok := v.(float64); ok {
		return n
	}
	return 0
}

func pollCommands(client *http.Client, server string, ident identity) ([]commandItem, error) {
	url := fmt.Sprintf("%s/api/v1/runtime/agents/%s/commands/pending?agent_token=%s", server, ident.AgentID, ident.AgentToken)
	req, err := http.NewRequest(http.MethodGet, url, nil)
	if err != nil {
		return nil, err
	}
	res, err := client.Do(req)
	if err != nil {
		return nil, err
	}
	defer res.Body.Close()
	if res.StatusCode >= 300 {
		b, _ := io.ReadAll(res.Body)
		return nil, fmt.Errorf("poll HTTP %d: %s", res.StatusCode, string(b))
	}
	var p struct {
		Commands []commandItem `json:"commands"`
	}
	if err := json.NewDecoder(res.Body).Decode(&p); err != nil {
		return nil, err
	}
	return p.Commands, nil
}

func postResult(client *http.Client, server string, ident identity, id string, code int, out, er string) error {
	return postJSONClient(client, fmt.Sprintf("%s/api/v1/runtime/agents/%s/commands/%s/result?agent_token=%s", server, ident.AgentID, id, ident.AgentToken), map[string]any{
		"exit_code": code,
		"stdout":    out,
		"stderr":    er,
	}, nil)
}

func runCommand(command string, shell bool) (int, string, string) {
	var cmd *exec.Cmd
	if runtime.GOOS == "windows" {
		cmd = exec.Command("cmd", "/C", command)
	} else if shell {
		cmd = exec.Command("bash", "-lc", command)
	} else {
		cmd = exec.Command("sh", "-c", command)
	}
	var out, er bytes.Buffer
	cmd.Stdout = &out
	cmd.Stderr = &er
	err := cmd.Run()
	code := 0
	if err != nil {
		if ee, ok := err.(*exec.ExitError); ok {
			code = ee.ExitCode()
		} else {
			code = 1
			er.WriteString(err.Error())
		}
	}
	return code, out.String(), er.String()
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

func sampleMetrics() (cpu, mem, disk *float64) {
	return nil, nil, nil
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

func enrollmentTokenPath() string {
	return filepath.Join(dataDir(), "enrollment_token")
}

func writeConfig(server string) error {
	_ = os.MkdirAll(dataDir(), 0755)
	cfg := map[string]any{"server_url": server, "agent_version": agentVersion}
	b, _ := json.MarshalIndent(cfg, "", "  ")
	return os.WriteFile(filepath.Join(dataDir(), "agent_config.json"), b, 0644)
}
