package main

import (
	"crypto/rand"
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
	// Best-effort: named mutex via temporary lock file in data dir.
	lock := filepath.Join(dataDir(), "support-client.lock")
	f, err := os.OpenFile(lock, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0600)
	if err != nil {
		// If stale (>24h), replace.
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

const pageHTML = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Bhudi Support</title>
<style>
:root{--bg:#0b1220;--card:#121a2b;--line:#1e2a44;--text:#e8eef9;--muted:#9db0d0;--accent:#1e6adf;--ok:#22c55e;--bad:#ef4444}
*{box-sizing:border-box}body{margin:0;font-family:Segoe UI,system-ui,sans-serif;background:linear-gradient(160deg,#0b1220,#0f1b33);color:var(--text);min-height:100vh}
.wrap{max-width:720px;margin:0 auto;padding:28px 18px 48px}
.brand{display:flex;align-items:center;gap:12px;margin-bottom:18px}
.logo{width:40px;height:40px;border-radius:10px;background:linear-gradient(135deg,#1e6adf,#36d6c3);display:grid;place-items:center;font-weight:700}
h1{margin:0;font-size:1.35rem}p.sub{margin:4px 0 0;color:var(--muted);font-size:.9rem}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px;margin-bottom:16px}
label{display:block;font-size:.8rem;color:var(--muted);margin:10px 0 6px}
input,textarea,select{width:100%;background:#0a1324;border:1px solid var(--line);border-radius:10px;color:var(--text);padding:10px 12px;font:inherit}
textarea{min-height:110px;resize:vertical}
.row{display:grid;grid-template-columns:1fr 1fr;gap:12px}
button{margin-top:14px;background:var(--accent);color:#fff;border:0;border-radius:10px;padding:11px 16px;font-weight:600;cursor:pointer}
button:disabled{opacity:.6;cursor:wait}
.msg{margin-top:10px;font-size:.9rem}.ok{color:var(--ok)}.bad{color:var(--bad)}
.ticket{border-top:1px solid var(--line);padding:12px 0}.ticket:first-child{border-top:0}
.meta{color:var(--muted);font-size:.8rem}
.pill{display:inline-block;padding:2px 8px;border-radius:999px;background:#1a2740;font-size:.75rem;margin-left:6px}
#status{font-size:.85rem;color:var(--muted);margin-bottom:12px}
</style>
</head>
<body>
<div class="wrap">
  <div class="brand"><div class="logo">B</div><div><h1>Bhudi Support</h1><p class="sub">Log a ticket from this PC · Cyber Bastion</p></div></div>
  <div id="status">Checking connection…</div>
  <div class="card">
    <form id="f">
      <label for="t">Title</label>
      <input id="t" required maxlength="200" placeholder="e.g. Printer offline / PC slow"/>
      <label for="d">Description</label>
      <textarea id="d" placeholder="What happened? Any error messages?"></textarea>
      <div class="row">
        <div>
          <label for="p">Priority</label>
          <select id="p"><option value="low">Low</option><option value="medium" selected>Medium</option><option value="high">High</option><option value="critical">Critical</option></select>
        </div>
        <div>
          <label for="c">Category</label>
          <select id="c"><option value="general">General</option><option value="hardware">Hardware</option><option value="software">Software</option><option value="network">Network</option><option value="security">Security</option></select>
        </div>
      </div>
      <button id="btn" type="submit">Submit ticket</button>
      <div id="msg" class="msg"></div>
    </form>
  </div>
  <div class="card" id="tickets">
    <h2 style="margin:0 0 8px;font-size:1.05rem">My tickets</h2>
    <div id="list" class="meta">Loading…</div>
  </div>
</div>
<script>
const session=new URLSearchParams(location.search).get('session');
const h={'X-Bhudi-Session':session,'Content-Type':'application/json'};
async function status(){
  try{
    const r=await fetch('/api/status',{headers:h});
    const j=await r.json();
    document.getElementById('status').textContent=j.online
      ?('Connected · agent '+String(j.agent_id||'').slice(0,8)+'…')
      :'Portal unreachable — ticket may fail until network is back';
  }catch(e){document.getElementById('status').textContent='Local UI only — cannot reach portal';}
}
async function load(){
  const el=document.getElementById('list');
  try{
    const r=await fetch('/api/tickets',{headers:h});
    const t=await r.text();
    let data; try{data=JSON.parse(t)}catch(_){el.textContent=t;return}
    const items=data.tickets||data||[];
    if(!items.length){el.textContent='No tickets yet from this device.';return}
    el.innerHTML=items.map(x=>`<div class="ticket"><strong>${esc(x.title||'Ticket')}</strong><span class="pill">${esc(x.status||'')}</span><span class="pill">${esc(x.priority||'')}</span><div class="meta">${esc(x.created_at||x.id||'')}</div></div>`).join('');
  }catch(e){el.textContent='Could not load tickets.';}
}
function esc(s){return String(s).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
document.getElementById('f').onsubmit=async e=>{
  e.preventDefault();
  const btn=document.getElementById('btn'), msg=document.getElementById('msg');
  btn.disabled=true; msg.textContent=''; msg.className='msg';
  try{
    const r=await fetch('/api/tickets',{method:'POST',headers:h,body:JSON.stringify({
      title:t.value, description:d.value, priority:p.value, category:c.value
    })});
    if(r.ok){msg.textContent='Ticket created.'; msg.className='msg ok'; t.value=''; d.value=''; load()}
    else{msg.textContent='Failed ('+r.status+'): '+await r.text(); msg.className='msg bad'}
  }catch(err){msg.textContent=String(err); msg.className='msg bad'}
  btn.disabled=false;
};
status(); load();
if(location.hash==='#tickets') document.getElementById('tickets').scrollIntoView();
</script>
</body></html>
