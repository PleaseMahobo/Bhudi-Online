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
    "time"

    "github.com/getlantern/systray"
)

type identity struct { AgentID string `json:"agent_id"`; AgentToken string `json:"agent_token"` }
type config struct { ServerURL string `json:"server_url"` }
type client struct { identity identity; server, session, baseURL string }
type createTicket struct { Title string `json:"title"`; Description string `json:"description"`; Priority string `json:"priority"`; Category string `json:"category,omitempty"`; Requester string `json:"requester,omitempty"` }

func main() {
    c, err := loadClient(); if err != nil { fmt.Fprintln(os.Stderr, "Bhudi Support Client:", err); os.Exit(1) }
    ln, err := net.Listen("tcp", "127.0.0.1:0"); if err != nil { os.Exit(1) }; c.baseURL="http://"+ln.Addr().String()
    mux:=http.NewServeMux(); mux.HandleFunc("/", c.page); mux.HandleFunc("/api/tickets", c.ticketAPI); go func(){ _=http.Serve(ln,mux) }()
    systray.Run(c.ready, func(){ _=ln.Close() })
}
func loadClient()(*client,error){
    dir:=dataDir(); deadline:=time.Now().Add(60*time.Second)
    for time.Now().Before(deadline) { ib,e:=os.ReadFile(filepath.Join(dir,"agent_identity.json")); if e==nil { var id identity; if json.Unmarshal(ib,&id)==nil&&id.AgentID!=""&&id.AgentToken!="" { cb,e:=os.ReadFile(filepath.Join(dir,"agent_config.json")); if e==nil { var cfg config; if json.Unmarshal(cb,&cfg)==nil&&strings.TrimSpace(cfg.ServerURL)!="" { b:=make([]byte,32);if _,e=rand.Read(b);e!=nil{return nil,e};return &client{identity:id,server:strings.TrimRight(cfg.ServerURL,"/"),session:base64.RawURLEncoding.EncodeToString(b)},nil } } } }; time.Sleep(2*time.Second) }
    return nil,fmt.Errorf("agent enrollment files were not available within 60 seconds")
}
func dataDir()string{ b:=os.Getenv("ProgramData");if b==""{b=os.Getenv("LOCALAPPDATA")};if b==""{b="."};return filepath.Join(b,"Bhudi","Agent") }
func(c *client)ready(){ systray.SetTitle("Bhudi");systray.SetTooltip("Bhudi Support");open:=systray.AddMenuItem("Open Ticket","Open a Bhudi support ticket");tickets:=systray.AddMenuItem("My Tickets","View your Bhudi tickets");systray.AddSeparator();quit:=systray.AddMenuItem("Exit","Exit Bhudi Support");go func(){for{select{case<-open.ClickedCh:c.open();case<-tickets.ClickedCh:c.open();case<-quit.ClickedCh:systray.Quit();return}}}() }
func(c *client)open(){ target:=c.baseURL+"/?session="+url.QueryEscape(c.session);if runtime.GOOS=="windows"{_=exec.Command("rundll32","url.dll,FileProtocolHandler",target).Start()}else{_=exec.Command("xdg-open",target).Start()} }
func(c *client)authorized(w http.ResponseWriter,r *http.Request)bool{if r.Header.Get("X-Bhudi-Session")!=c.session{http.Error(w,"unauthorized",401);return false};return true}
func(c *client)page(w http.ResponseWriter,r *http.Request){ if r.URL.Query().Get("session")!=c.session&&!c.authorized(w,r){return};w.Header().Set("Cache-Control","no-store");w.Header().Set("Content-Type","text/html; charset=utf-8");fmt.Fprint(w,"<html><body><h1>Bhudi Support</h1><p>Use the tray menu to open support.</p></body></html>") }
func(c *client)ticketAPI(w http.ResponseWriter,r *http.Request){if !c.authorized(w,r){return};endpoint:=c.server+"/api/v1/agent-support/tickets?agent_id="+url.QueryEscape(c.identity.AgentID);var req *http.Request;var err error;switch r.Method{case http.MethodPost:var p createTicket;if err=json.NewDecoder(r.Body).Decode(&p);err!=nil{http.Error(w,err.Error(),400);return};body,_:=json.Marshal(p);req,err=http.NewRequest(http.MethodPost,endpoint,strings.NewReader(string(body)));if err==nil{req.Header.Set("Content-Type","application/json")};case http.MethodGet:req,err=http.NewRequest(http.MethodGet,endpoint,nil);default:http.Error(w,"method not allowed",405);return};if err!=nil{http.Error(w,err.Error(),500);return};req.Header.Set("X-Bhudi-Agent-Token",c.identity.AgentToken);res,err:=http.DefaultClient.Do(req);if err!=nil{http.Error(w,err.Error(),502);return};defer res.Body.Close();w.Header().Set("Content-Type","application/json");w.WriteHeader(res.StatusCode);_,_=io.Copy(w,res.Body)}
