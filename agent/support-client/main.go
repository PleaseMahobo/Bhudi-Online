package main

import (
	"crypto/rand"
	_ "embed"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"sync"
	"time"

	"github.com/getlantern/systray"
)

//go:embed page.html
var pageHTML string

const appName = "Bhudi Support"

type identity struct {
	AgentID    string `json:"agent_id"`
	AgentToken string `json:"agent_token"`
}

type config struct {
	ServerURL string `json:"server_url"`
}

type client struct {
	identity identity
	server   string
	session  string
	baseURL  string
	mu       sync.Mutex
	online   bool
}

type createTicket struct {
	Title       string `json:"title"`
	Description string `json:"description"`
	Priority    string `json:"priority"`
	Category    string `json:"category,omitempty"`
	Requester   string `json:"requester,omitempty"`
}

func main() {
	if alreadyRunning() {
		fmt.Fprintln(os.Stderr, appName+": already running")
		os.Exit(0)
	}
	c, err := loadClient()
	if err != nil {
		fmt.Fprintln(os.Stderr, appName+":", err)
		os.Exit(1)
	}
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		os.Exit(1)
	}
	c.baseURL = "http://" + ln.Addr().String()
	mux := http.NewServeMux()
	mux.HandleFunc("/", c.page)
	mux.HandleFunc("/api/tickets", c.ticketAPI)
	mux.HandleFunc("/api/status", c.statusAPI)
	go func() { _ = http.Serve(ln, mux) }()
	go c.probeLoop()
	systray.Run(c.ready, func() { _ = ln.Close() })
}

func alreadyRunning() bool {
	if runtime.GOOS != "windows" {
		return false
	}
	lock := filepath.Join(dataDir(), "support-client.lock")
	f, err := os.OpenFile(lock, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0600)
	if err != nil {
		if st, e := os.Stat(lock); e == nil && time.Since(st.ModTime()) > 24*time.Hour {
			_ = os.Remove(lock)
			f, err = os.OpenFile(lock, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0600)
			if err != nil {
				return true
			}
		} else {
			return true
		}
	}
	_, _ = fmt.Fprintf(f, "%d\n", os.Getpid())
	_ = f.Close()
	return false
}

func loadClient() (*client, error) {
	dir := dataDir()
	deadline := time.Now().Add(90 * time.Second)
	for time.Now().Before(deadline) {
		ib, e := os.ReadFile(filepath.Join(dir, "agent_identity.json"))
		if e == nil {
			var id identity
			if json.Unmarshal(ib, &id) == nil && id.AgentID != "" && id.AgentToken != "" {
				cb, e := os.ReadFile(filepath.Join(dir, "agent_config.json"))
				if e == nil {
					var cfg config
					if json.Unmarshal(cb, &cfg) == nil && strings.TrimSpace(cfg.ServerURL) != "" {
						b := make([]byte, 32)
						if _, e = rand.Read(b); e != nil {
							return nil, e
						}
						return &client{
							identity: id,
							server:   strings.TrimRight(cfg.ServerURL, "/"),
							session:  base64.RawURLEncoding.EncodeToString(b),
							online:   true,
						}, nil
					}
				}
			}
		}
		time.Sleep(2 * time.Second)
	}
	return nil, fmt.Errorf("agent enrollment files were not available within 90 seconds (install/run bhudi-agent first)")
}

func dataDir() string {
	b := os.Getenv("ProgramData")
	if b == "" {
		b = os.Getenv("LOCALAPPDATA")
	}
	if b == "" {
		b = "."
	}
	return filepath.Join(b, "Bhudi", "Agent")
}

func (c *client) ready() {
	systray.SetTitle("Bhudi")
	systray.SetTooltip("Bhudi Support — log a ticket with IT")
	open := systray.AddMenuItem("Open ticket…", "Create a support ticket")
	tickets := systray.AddMenuItem("My tickets", "View tickets from this PC")
	systray.AddSeparator()
	statusItem := systray.AddMenuItem("Status: checking…", "Agent / portal status")
	statusItem.Disable()
	systray.AddSeparator()
	quit := systray.AddMenuItem("Exit", "Exit Bhudi Support")
	go func() {
		for {
			c.mu.Lock()
			on := c.online
			c.mu.Unlock()
			if on {
				statusItem.SetTitle("Status: connected")
				systray.SetTooltip("Bhudi Support — connected")
			} else {
				statusItem.SetTitle("Status: offline / unreachable")
				systray.SetTooltip("Bhudi Support — offline")
			}
			time.Sleep(15 * time.Second)
		}
	}()
	go func() {
		for {
			select {
			case <-open.ClickedCh:
				c.open("")
			case <-tickets.ClickedCh:
				c.open("#tickets")
			case <-quit.ClickedCh:
				systray.Quit()
				return
			}
		}
	}()
}

func (c *client) open(hash string) {
	target := c.baseURL + "/?session=" + url.QueryEscape(c.session) + hash
	if runtime.GOOS == "windows" {
		_ = exec.Command("rundll32", "url.dll,FileProtocolHandler", target).Start()
	} else {
		_ = exec.Command("xdg-open", target).Start()
	}
}

func (c *client) probeLoop() {
	for {
		ok := false
		req, err := http.NewRequest(http.MethodGet, c.server+"/health", nil)
		if err == nil {
			cli := &http.Client{Timeout: 5 * time.Second}
			res, err := cli.Do(req)
			if err == nil {
				_ = res.Body.Close()
				ok = res.StatusCode < 500
			}
		}
		c.mu.Lock()
		c.online = ok
		c.mu.Unlock()
		time.Sleep(30 * time.Second)
	}
}

func (c *client) authorized(w http.ResponseWriter, r *http.Request) bool {
	if r.Header.Get("X-Bhudi-Session") != c.session {
		http.Error(w, "unauthorized", http.StatusUnauthorized)
		return false
	}
	return true
}

func (c *client) statusAPI(w http.ResponseWriter, r *http.Request) {
	if !c.authorized(w, r) {
		return
	}
	c.mu.Lock()
	on := c.online
	c.mu.Unlock()
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(map[string]any{
		"online":   on,
		"agent_id": c.identity.AgentID,
		"server":   c.server,
	})
}

func (c *client) page(w http.ResponseWriter, r *http.Request) {
	sess := r.URL.Query().Get("session")
	if sess != c.session && r.Header.Get("X-Bhudi-Session") != c.session {
		http.Error(w, "unauthorized", http.StatusUnauthorized)
		return
	}
	w.Header().Set("Cache-Control", "no-store")
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	fmt.Fprint(w, pageHTML)
}

func (c *client) ticketAPI(w http.ResponseWriter, r *http.Request) {
	if !c.authorized(w, r) {
		return
	}
	endpoint := c.server + "/api/v1/agent-support/tickets?agent_id=" + url.QueryEscape(c.identity.AgentID)
	var req *http.Request
	var err error
	switch r.Method {
	case http.MethodPost:
		var p createTicket
		if err = json.NewDecoder(r.Body).Decode(&p); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		p.Title = strings.TrimSpace(p.Title)
		if p.Title == "" {
			http.Error(w, "title required", http.StatusBadRequest)
			return
		}
		if p.Priority == "" {
			p.Priority = "medium"
		}
		body, _ := json.Marshal(p)
		req, err = http.NewRequest(http.MethodPost, endpoint, strings.NewReader(string(body)))
		if err == nil {
			req.Header.Set("Content-Type", "application/json")
		}
	case http.MethodGet:
		req, err = http.NewRequest(http.MethodGet, endpoint, nil)
	default:
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	req.Header.Set("X-Bhudi-Agent-Token", c.identity.AgentToken)
	res, err := http.DefaultClient.Do(req)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadGateway)
		return
	}
	defer res.Body.Close()
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(res.StatusCode)
	_, _ = io.Copy(w, res.Body)
}
