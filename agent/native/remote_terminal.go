package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os/exec"
	"runtime"
	"strings"
	"sync"
	"time"

	"github.com/gorilla/websocket"
)

// startRemoteTerminal connects to the backend session WebSocket and streams a local shell.
// Protocol mirrors agent/streaming_session.py (terminal path).
func startRemoteTerminal(serverURL, agentID string, command map[string]any) map[string]any {
	payload, _ := command["payload"].(map[string]any)
	if payload == nil {
		payload = map[string]any{}
	}
	sessionID := strVal(payload["session_id"])
	if sessionID == "" {
		return resultErr("session_id is required for interactive terminal")
	}

	shellName := strVal(payload["shell"])
	cwd := strVal(payload["working_directory"])

	wsURL, err := sessionWSURL(serverURL, sessionID, agentID)
	if err != nil {
		return resultErr(err.Error())
	}

	go runTerminalSession(wsURL, sessionID, shellName, cwd)

	return map[string]any{
		"exit_code": 0,
		"stdout":    "started remote terminal session " + sessionID,
		"stderr":    "",
		"metadata": map[string]any{
			"session_id":   sessionID,
			"streaming":    true,
			"stream_path":  "/api/v1/remote-access/sessions/" + sessionID + "/dashboard",
			"session_type": "terminal",
		},
	}
}

func sessionWSURL(serverURL, sessionID, agentID string) (string, error) {
	u, err := url.Parse(strings.TrimRight(serverURL, "/"))
	if err != nil {
		return "", err
	}
	scheme := "wss"
	if u.Scheme == "http" {
		scheme = "ws"
	}
	host := u.Host
	if host == "" {
		host = u.Path
	}
	return fmt.Sprintf("%s://%s/api/v1/remote-access/sessions/%s/agent/%s", scheme, host, sessionID, agentID), nil
}

func runTerminalSession(wsURL, sessionID, shellName, cwd string) {
	fmt.Println("[remote-terminal] connecting", wsURL)
	dialer := websocket.Dialer{HandshakeTimeout: 20 * time.Second}
	conn, resp, err := dialer.Dial(wsURL, nil)
	if err != nil {
		status := 0
		if resp != nil {
			status = resp.StatusCode
		}
		fmt.Printf("[remote-terminal] dial failed status=%d err=%v\n", status, err)
		return
	}
	defer conn.Close()

	_ = conn.SetReadDeadline(time.Now().Add(30 * time.Second))
	_, msg, err := conn.ReadMessage()
	if err != nil {
		fmt.Println("[remote-terminal] read attach:", err)
		return
	}
	fmt.Println("[remote-terminal] attached:", string(msg)[:min(120, len(msg))])
	_ = conn.SetReadDeadline(time.Time{})

	shellPath := resolveShell(shellName)
	var cmd *exec.Cmd
	if runtime.GOOS == "windows" {
		if strings.Contains(strings.ToLower(shellPath), "powershell") {
			cmd = exec.Command(shellPath, "-NoLogo", "-NoExit")
		} else {
			cmd = exec.Command(shellPath)
		}
	} else {
		cmd = exec.Command(shellPath)
	}
	if cwd != "" {
		cmd.Dir = cwd
	}

	stdin, err := cmd.StdinPipe()
	if err != nil {
		fmt.Println("[remote-terminal] stdin:", err)
		return
	}
	stdout, err := cmd.StdoutPipe()
	if err != nil {
		fmt.Println("[remote-terminal] stdout:", err)
		return
	}
	stderr, err := cmd.StderrPipe()
	if err != nil {
		fmt.Println("[remote-terminal] stderr:", err)
		return
	}
	if err := cmd.Start(); err != nil {
		fmt.Println("[remote-terminal] start shell:", err)
		_ = writeJSON(conn, map[string]any{"type": "error", "session_id": sessionID, "message": err.Error()})
		return
	}

	_ = writeJSON(conn, map[string]any{
		"type":       "terminal_ready",
		"session_id": sessionID,
		"shell":      shellPath,
		"platform":   runtime.GOOS,
		"cwd":        cwd,
	})

	var wg sync.WaitGroup
	stop := make(chan struct{})
	var once sync.Once
	closeStop := func() { once.Do(func() { close(stop) }) }

	pump := func(r io.Reader, stream string) {
		defer wg.Done()
		br := bufio.NewReader(r)
		buf := make([]byte, 4096)
		for {
			n, err := br.Read(buf)
			if n > 0 {
				_ = writeJSON(conn, map[string]any{
					"type":       "output",
					"session_id": sessionID,
					"stream":     stream,
					"data":       string(buf[:n]),
				})
			}
			if err != nil {
				return
			}
		}
	}
	wg.Add(2)
	go pump(stdout, "stdout")
	go pump(stderr, "stderr")

	go func() {
		defer closeStop()
		for {
			_, raw, err := conn.ReadMessage()
			if err != nil {
				return
			}
			var message map[string]any
			if json.Unmarshal(raw, &message) != nil {
				continue
			}
			msgType := strVal(message["type"])
			if msgType == "session_attached" {
				continue
			}
			if msgType == "dashboard_message" {
				inner, _ := message["payload"].(map[string]any)
				if inner == nil {
					continue
				}
				switch strVal(inner["type"]) {
				case "input":
					_, _ = io.WriteString(stdin, strVal(inner["data"]))
				case "command":
					_, _ = io.WriteString(stdin, strVal(inner["command"])+"\n")
				case "resize":
					_ = writeJSON(conn, map[string]any{
						"type":       "resize_ack",
						"session_id": sessionID,
						"rows":       inner["rows"],
						"cols":       inner["cols"],
					})
				case "close":
					_ = writeJSON(conn, map[string]any{
						"type":       "session_closed",
						"session_id": sessionID,
						"reason":     "closed_by_operator",
					})
					_ = stdin.Close()
					if cmd.Process != nil {
						_ = cmd.Process.Kill()
					}
					return
				}
			}
			if msgType == "close" {
				_ = stdin.Close()
				if cmd.Process != nil {
					_ = cmd.Process.Kill()
				}
				return
			}
		}
	}()

	<-stop
	_ = stdin.Close()
	_ = cmd.Wait()
	wg.Wait()
	fmt.Println("[remote-terminal] session ended", sessionID)
}

func resolveShell(name string) string {
	n := strings.ToLower(strings.TrimSpace(name))
	if runtime.GOOS == "windows" {
		switch n {
		case "cmd":
			return "cmd.exe"
		case "powershell", "pwsh", "":
			return "powershell.exe"
		default:
			return name
		}
	}
	switch n {
	case "zsh":
		return "/bin/zsh"
	case "sh":
		return "/bin/sh"
	case "bash", "":
		return "/bin/bash"
	default:
		if strings.HasPrefix(name, "/") {
			return name
		}
		return "/bin/bash"
	}
}

func writeJSON(conn *websocket.Conn, v any) error {
	b, err := json.Marshal(v)
	if err != nil {
		return err
	}
	_ = conn.SetWriteDeadline(time.Now().Add(15 * time.Second))
	return conn.WriteMessage(websocket.TextMessage, b)
}

func strVal(v any) string {
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

func resultErr(msg string) map[string]any {
	return map[string]any{"exit_code": 1, "stdout": "", "stderr": msg}
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

var _ = http.StatusOK
