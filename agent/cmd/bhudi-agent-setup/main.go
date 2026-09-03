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
)

type bootstrap struct { ServerURL string `json:"server_url"`; EnrollmentToken string `json:"enrollment_token"` }

type installedIdentity struct { AgentID string `json:"agent_id"`; AgentToken string `json:"agent_token"` }

func main() {
	if runtime.GOOS == "windows" && len(os.Args) == 1 {
		runInstallerGUI()
		return
	}
	if runtime.GOOS == "windows" && len(os.Args) > 1 && strings.EqualFold(os.Args[1], "install-worker") {
		os.Args = append([]string{os.Args[0]}, os.Args[2:]...)
	}
	ensureElevated()
	boot, err := readBootstrap(); if err != nil { fail("This is not a customer-specific Bhudi installer. Download a fresh installer from the Bhudi portal.\nDetails: "+err.Error()) }
	server := strings.TrimRight(strings.TrimSpace(boot.ServerURL), "/"); if server == "" { server = defaultServer }
	if strings.TrimSpace(boot.EnrollmentToken) == "" { fail("Customer enrollment information is missing. Download a fresh installer from the Bhudi portal.") }
	if runtime.GOOS != "windows" { fail("This installer is for Windows.") }

	fmt.Println("========================================"); fmt.Println("  Bhudi Agent Setup"); fmt.Println("========================================")
	tmp, err := os.MkdirTemp("", "bhudi-setup-*"); if err != nil { fail(err.Error()) }; defer os.RemoveAll(tmp)

	agentPath := filepath.Join(tmp, "bhudi-agent.exe")
	fmt.Println("[1/4] Preparing bundled Bhudi agent..."); if err := installBundledAgent(agentPath); err != nil { fail("bundled agent: "+err.Error()) }

	identity := filepath.Join(os.Getenv("ProgramData"), "Bhudi", "Agent", "agent_identity.json")
	if !hasValidIdentity(identity) {
		fmt.Println("[2/4] Enrolling endpoint before installing Windows service...")
		cmd := exec.Command(agentPath, "enroll", "-server", server)
		cmd.Env = append(os.Environ(), "BHUDI_ENROLLMENT_TOKEN="+boot.EnrollmentToken)
		cmd.Stdout = os.Stdout; cmd.Stderr = os.Stderr; cmd.Stdin = os.Stdin
		if err := cmd.Run(); err != nil { fail("agent enrollment failed: "+err.Error()) }
		if !hasValidIdentity(identity) { fail("agent enrollment completed without creating agent_identity.json") }
	} else {
		fmt.Println("[2/4] Existing agent identity found; reusing this device identity...")
	}

	fmt.Println("Installing Windows service and starting agent...")
	cmd := exec.Command(agentPath, "install", "-server", server)
	cmd.Stdout = os.Stdout; cmd.Stderr = os.Stderr; cmd.Stdin = os.Stdin
	if err := cmd.Run(); err != nil { fail("agent installation failed: "+err.Error()) }

	fmt.Println("[3/4] Installing Bhudi Support Client...")
	supportDir := filepath.Join(os.Getenv("ProgramFiles"), "Bhudi", "Support")
	if supportDir == "" { supportDir = filepath.Join(os.Getenv("ProgramData"), "Bhudi", "Support") }
	if err := os.MkdirAll(supportDir, 0755); err != nil { fail("support directory: "+err.Error()) }
	supportPath := filepath.Join(supportDir, "bhudi-support.exe")
	if err := download(supportURL, supportPath); err != nil { fail("support-client download: "+err.Error()) }
	if !hasValidIdentity(identity) { fail("agent identity disappeared after service installation") }
	if err := startSupportClient(supportPath); err != nil { fail("support-client start: "+err.Error()) }

	fmt.Println("[4/4] Installation complete"); fmt.Println("The Bhudi agent and support client are installed and enrolled."); time.Sleep(2*time.Second)
}

func installBundledAgent(dest string) error {
	if len(bundledAgent) == 0 { return fmt.Errorf("bundled Bhudi agent payload is empty") }
	if err := os.WriteFile(dest, bundledAgent, 0755); err != nil { return err }
	return nil
}

func hasValidIdentity(path string) bool {
	data, err := os.ReadFile(path); if err != nil { return false }
	var id installedIdentity
	return json.Unmarshal(data, &id) == nil && strings.TrimSpace(id.AgentID) != "" && strings.TrimSpace(id.AgentToken) != ""
}

func startSupportClient(path string) error {
	cmd := exec.Command(path); if err:=cmd.Start(); err!=nil{return err}
	_ = exec.Command("reg.exe","ADD",`HKCU\Software\Microsoft\Windows\CurrentVersion\Run`,"BhudiSupport","/REG_SZ",path,"/F").Run()
	return nil
}
func readBootstrap() (bootstrap,error) { exe,err:=os.Executable();if err!=nil{return bootstrap{},err};f,err:=os.Open(exe);if err!=nil{return bootstrap{},err};defer f.Close();stat,err:=f.Stat();if err!=nil{return bootstrap{},err};footerSize:=int64(len(magic)+8);if stat.Size()<footerSize{return bootstrap{},fmt.Errorf("customer bootstrap payload not found")};if _,err=f.Seek(-footerSize,io.SeekEnd);err!=nil{return bootstrap{},err};footer:=make([]byte,footerSize);if _,err=io.ReadFull(f,footer);err!=nil{return bootstrap{},err};if string(footer[8:])!=magic{return bootstrap{},fmt.Errorf("invalid customer bootstrap footer")};length:=binary.LittleEndian.Uint64(footer[:8]);if length==0||length>1024*1024||int64(length)+footerSize>stat.Size(){return bootstrap{},fmt.Errorf("invalid customer bootstrap length")};if _,err=f.Seek(-(footerSize+int64(length)),io.SeekEnd);err!=nil{return bootstrap{},err};payload:=make([]byte,length);if _,err=io.ReadFull(f,payload);err!=nil{return bootstrap{},err};var boot bootstrap;if err=json.Unmarshal(payload,&boot);err!=nil{return bootstrap{},fmt.Errorf("invalid customer bootstrap payload")};return boot,nil }
func download(url,dest string) error { client:=&http.Client{Timeout:2*time.Minute};resp,err:=client.Get(url);if err!=nil{return err};defer resp.Body.Close();if resp.StatusCode!=http.StatusOK{return fmt.Errorf("HTTP %d",resp.StatusCode)};f,err:=os.Create(dest);if err!=nil{return err};defer f.Close();_,err=io.Copy(f,resp.Body);return err }
func fail(msg string){fmt.Fprintln(os.Stderr,"ERROR:",msg);fmt.Println("Press Enter to exit...");_,_=fmt.Fscanln(os.Stdin);os.Exit(1)}
