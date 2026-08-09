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
		if err := cycle(client, cfg.Server, ident); err != nil {
			fmt.Println("[error]", err)
		}
		time.Sleep(time.Duration(cfg.Interval) * time.Second)
	}
}

func cycle(client *http.Client, server string, ident identity) error {
	if err := sendHeartbeat(client, server, ident); err != nil {
		return err
	}

	for _, cmd := range pollEnterpriseCommands(client, server, ident) {
		cmdID := firstString(cmd, "command_id", "id")
		cmdType := firstString(cmd, "command_type")
		fmt.Printf("[enterprise-command] %s type=%s\n", cmdID, cmdType)
		_ = markEnterpriseSent(client, server, ident, cmdID)
		result := executeEnterpriseCommand(server, ident, cmd)
		_ = postEnterpriseResult(client, server, ident, cmdID, result)
		fmt.Printf("[enterprise-result] exit=%v\n", result["exit_code"])
	}

	cmds, err := pollCommands(client, server, ident)
	if err != nil {
		return err
	}
	for _, c := range cmds {
		fmt.Printf("[command] %s type=%s cmd=%s\n", c.CommandID, c.CommandType, c.Command)
		if c.CommandType == "remote.desktop.start" || c.CommandType == "remote.terminal.start" {
			cmdMap := map[string]any{
				"command_id":   c.CommandID,
				"command_type": c.CommandType,
				"payload":      c.Payload,
			}
			result := executeEnterpriseCommand(server, ident, cmdMap)
			exitCode := 0
			if v, ok := result["exit_code"].(int); ok {
				exitCode = v
			} else if v, ok := result["exit_code"].(float64); ok {
				exitCode = int(v)
			}
			stdout, _ := result["stdout"].(string)
			stderr, _ := result["stderr"].(string)
			_ = postResult(client, server, ident, c.CommandID, exitCode, stdout, stderr)
			fmt.Printf("[result] remote session exit=%d\n", exitCode)
			continue
		}
		exitCode, stdout, stderr := runCommand(c.Command, c.Shell)
		if err := postResult(client, server, ident, c.CommandID, exitCode, stdout, stderr); err != nil {
			fmt.Println("[result-error]", err)
			continue
		}
		fmt.Printf("[result] exit=%d\n", exitCode)
	}
	return nil
}

func executeEnterpriseCommand(server string, ident identity, cmd map[string]any) map[string]any {
	cmdType := firstString(cmd, "command_type")
	payload, _ := cmd["payload"].(map[string]any)
	if payload == nil {
		payload = map[string]any{}
	}

	switch cmdType {
	case "remote.desktop.start":
		return startRemoteDesktop(server, ident.AgentID, cmd)

	case "remote.terminal.start":
		interactive := true
		if v, ok := payload["interactive"]; ok {
			if b, ok := v.(bool); ok {
				interactive = b
			}
		}
		if interactive {
			return startRemoteTerminal(server, ident.AgentID, cmd)
		}
		shellCmd := firstString(payload, "command", "script")
		if shellCmd == "" {
			return map[string]any{"exit_code": 1, "stdout": "", "stderr": "no command"}
		}
		code, out, errOut := runCommand(shellCmd, true)
		return map[string]any{"exit_code": code, "stdout": out, "stderr": errOut}

	case "remote.cmd", "remote.powershell", "remote_script", "remote_powershell":
		shellCmd := firstString(payload, "command", "script")
		if shellCmd == "" {
			return map[string]any{"exit_code": 1, "stdout": "", "stderr": "no command"}
		}
		code, out, errOut := runCommand(shellCmd, true)
		return map[string]any{"exit_code": code, "stdout": out, "stderr": errOut}

	case "remote.reboot":
		if runtime.GOOS == "windows" {
			code, out, errOut := runCommand("shutdown /r /t 5", true)
			return map[string]any{"exit_code": code, "stdout": out, "stderr": errOut}
		}
		code, out, errOut := runCommand("sudo reboot", true)
		return map[string]any{"exit_code": code, "stdout": out, "stderr": errOut}

	default:
		if shellCmd := firstString(payload, "command", "script"); shellCmd != "" {
			code, out, errOut := runCommand(shellCmd, true)
			return map[string]any{"exit_code": code, "stdout": out, "stderr": errOut}
		}
		return map[string]any{"exit_code": 1, "stdout": "", "stderr": "unsupported command_type: " + cmdType}
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
	if res.StatusCode == 404 || res.StatusCode >= 300 {
		return nil
	}
	body, _ := io.ReadAll(res.Body)
	var list []map[string]any
	if json.Unmarshal(body, &list) == nil {
		return list
	}
	var wrap struct {
		Commands []map[string]any `json:"commands"`
	}
	if json.Unmarshal(body, &wrap) == nil {
		return wrap.Commands
	}
	return nil
}

func markEnterpriseSent(client *http.Client, server string, ident identity, commandID string) error {
	if commandID == "" {
		return nil
	}
	url := server + "/api/v1/agent/" + ident.AgentID + "/commands/" + commandID + "/sent"
	req, err := http.NewRequest(http.MethodPost, url, nil)
	if err != nil {
		return err
	}
	res, err := client.Do(req)
	if err != nil {
		return err
	}
	defer res.Body.Close()
	return nil
}

func postEnterpriseResult(client *http.Client, server string, ident identity, commandID string, result map[string]any) error {
	if commandID == "" {
		return nil
	}
	exitCode := 1
	if v, ok := result["exit_code"].(int); ok {
		exitCode = v
	} else if v, ok := result["exit_code"].(float64); ok {
		exitCode = int(v)
	}
	endpoint := "failed"
	var body any
	if exitCode == 0 {
		endpoint = "completed"
		body = result
	} else {
		msg := firstString(result, "stderr", "stdout")
		if msg == "" {
			msg = "remote command failed"
		}
		body = map[string]any{"message": msg}
	}
	url := server + "/api/v1/agent/" + ident.AgentID + "/commands/" + commandID + "/" + endpoint
	return postJSONClient(client, url, body, nil)
}

func firstString(m map[string]any, keys ...string) string {
	for _, k := range keys {
		if v, ok := m[k]; ok && v != nil {
			s := strings.TrimSpace(fmt.Sprint(v))
			if s != "" && s != "<nil>" {
				return s
			}
		}
	}
	return ""
}

func loadOrEnroll(server string) (identity, error) {
	path := identityPath()
	if data, err := os.ReadFile(path); err == nil {
		var id identity
		if json.Unmarshal(data, &id) == nil && id.AgentID != "" && id.AgentToken != "" {
			return id, nil
		}
	}
	return enroll(server)
}

func enroll(server string) (identity, error) {
	body := enrollReq{
		Hostname:     hostname(),
		AgentVersion: agentVersion,
		Platform:     runtime.GOOS + "/" + runtime.GOARCH + " " + runtime.Version(),
	}
	var resp enrollResp
	if err := postJSON(server+"/api/v1/runtime/enroll", body, &resp); err != nil {
		return identity{}, err
	}
	id := identity{AgentID: resp.AgentID, AgentToken: resp.AgentToken}
	_ = os.MkdirAll(filepath.Dir(identityPath()), 0755)
	data, _ := json.MarshalIndent(id, "", "  ")
	_ = os.WriteFile(identityPath(), data, 0600)
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
	pending, _ := raw["pending_commands"].(float64)
	fmt.Printf("[heartbeat] ok pending=%.0f\n", pending)
	return nil
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
	var payload struct {
		Commands []commandItem `json:"commands"`
	}
	if err := json.NewDecoder(res.Body).Decode(&payload); err != nil {
		return nil, err
	}
	return payload.Commands, nil
}

func postResult(client *http.Client, server string, ident identity, commandID string, exitCode int, stdout, stderr string) error {
	url := fmt.Sprintf("%s/api/v1/runtime/agents/%s/commands/%s/result?agent_token=%s", server, ident.AgentID, commandID, ident.AgentToken)
	body := map[string]any{"exit_code": exitCode, "stdout": stdout, "stderr": stderr}
	return postJSONClient(client, url, body, nil)
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

func writeConfig(server string) error {
	_ = os.MkdirAll(dataDir(), 0755)
	cfg := map[string]any{"server_url": server, "agent_version": agentVersion}
	b, _ := json.MarshalIndent(cfg, "", "  ")
	return os.WriteFile(filepath.Join(dataDir(), "agent_config.json"), b, 0644)
}
