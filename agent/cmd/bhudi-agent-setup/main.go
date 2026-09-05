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

var installerLog *os.File

func installerLogPath() string {
	base := os.Getenv("ProgramData")
	if strings.TrimSpace(base) == "" { base = os.TempDir() }
	return filepath.Join(base, "Bhudi", "Logs", "installer.log")
}

func startInstallerLog() {
	path := installerLogPath()
	if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil { return }
	f, err := os.OpenFile(path, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0644)
	if err != nil { return }
	installerLog = f
	fmt.Fprintf(installerLog, "\n===== Bhudi installer started %s =====\n", time.Now().Format(time.RFC3339))
}

func logInstaller(format string, args ...any) {
	if installerLog != nil { fmt.Fprintf(installerLog, format+"\n", args...) }
}

func main() {
	if runtime.GOOS == "windows" {
		if len(os.Args) < 2 || (len(os.Args) >= 2 && strings.EqualFold(os.Args[1], "elevated-ui")) {
			runInstallerGUI()
			return
		}
	}
	if len(os.Args) >= 2 && strings.EqualFold(os.Args[1], "install-worker") {
		runInstallWorker()
		return
	}
	fail("This installer must be started normally from Windows Explorer.")
}

func runInstallWorker() {
	startInstallerLog()
	if installerLog != nil { defer installerLog.Close() }
	logInstaller("Installer worker started; executable=%s", os.Args[0])
	boot, err := readBootstrap()
	if err != nil { fail("This is not a customer-specific Bhudi installer. Download a fresh installer from the Bhudi portal.\nDetails: " + err.Error()) }
	server := strings.TrimRight(strings.TrimSpace(boot.ServerURL), "/")
	if server == "" { server = defaultServer }
	if strings.TrimSpace(boot.EnrollmentToken) == "" { fail("Customer enrollment information is missing. Download a fresh installer from the Bhudi portal.") }
	if runtime.GOOS != "windows" { fail("This installer is for Windows.") }

	tmp, err := os.MkdirTemp("", "bhudi-setup-")
	if err != nil { fail(err.Error()) }
	defer os.RemoveAll(tmp)

	agentPath := filepath.Join(tmp, "bhudi-agent.exe")
	fmt.Println("[1/4] Preparing bundled Bhudi agent...")
	logInstaller("[1/4] Preparing bundled Bhudi agent at %s", agentPath)
	if err := installBundledAgent(agentPath); err != nil { fail("bundled agent: " + err.Error()) }

	identity := filepath.Join(os.Getenv("ProgramData"), "Bhudi", "Agent", "agent_identity.json")
	if !hasValidIdentity(identity) {
		fmt.Println("[2/4] Enrolling endpoint before installing Windows service...")
		logInstaller("[2/4] Enrolling endpoint against %s", server)
		cmd := exec.Command(agentPath, "enroll", "-server", server)
		cmd.Env = append(os.Environ(), "BHUDI_ENROLLMENT_TOKEN="+boot.EnrollmentToken)
		cmd.Stdout, cmd.Stderr = io.MultiWriter(os.Stdout, installerLogWriter()), io.MultiWriter(os.Stderr, installerLogWriter())
		if err := cmd.Run(); err != nil { fail("agent enrollment failed: " + err.Error()) }
		if !hasValidIdentity(identity) { fail("agent enrollment completed without creating agent_identity.json") }
	} else {
		fmt.Println("[2/4] Existing agent identity found; reusing this device identity...")
	}

	fmt.Println("[3/4] Installing Windows service and starting agent...")
	logInstaller("[3/4] Installing Windows service")
	cmd := exec.Command(agentPath, "install", "-server", server)
	cmd.Stdout, cmd.Stderr = io.MultiWriter(os.Stdout, installerLogWriter()), io.MultiWriter(os.Stderr, installerLogWriter())
	if err := cmd.Run(); err != nil { fail("agent installation failed: " + err.Error()) }

	fmt.Println("[4/4] Installing Bhudi Support Client...")
	logInstaller("[4/4] Installing Support Client from %s", supportURL)
	supportDir := filepath.Join(os.Getenv("ProgramFiles"), "Bhudi", "Support")
	if supportDir == "" { supportDir = filepath.Join(os.Getenv("ProgramData"), "Bhudi", "Support") }
	if err := os.MkdirAll(supportDir, 0755); err != nil { fail("support directory: " + err.Error()) }
	supportPath := filepath.Join(supportDir, "bhudi-support.exe")
	if err := download(supportURL, supportPath); err != nil { fail("support-client download: " + err.Error()) }
	if !hasValidIdentity(identity) { fail("agent identity disappeared after service installation") }
	if err := startSupportClient(supportPath); err != nil { fail("support-client start: " + err.Error()) }

	fmt.Println("Installation complete")
	logInstaller("Installation complete")
}

func installBundledAgent(dest string) error {
	if len(bundledAgent) == 0 { return fmt.Errorf("bundled Bhudi agent payload is empty") }
	return os.WriteFile(dest, bundledAgent, 0755)
}

func hasValidIdentity(path string) bool {
	data, err := os.ReadFile(path); if err != nil { return false }
	var id installedIdentity
	return json.Unmarshal(data, &id) == nil && strings.TrimSpace(id.AgentID) != "" && strings.TrimSpace(id.AgentToken) != ""
}

func startSupportClient(path string) error {
	cmd := exec.Command(path); if err:=cmd.Start(); err!=nil{return err}
	_ = exec.Command("reg.exe","ADD",`HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run`,"BhudiSupport","/REG_SZ",path,"/F").Run()
	return nil
}
func readBootstrap() (bootstrap,error) { exe,err:=os.Executable();if err!=nil{return bootstrap{},err};f,err:=os.Open(exe);if err!=nil{return bootstrap{},err};defer f.Close();stat,err:=f.Stat();if err!=nil{return bootstrap{},err};footerSize:=int64(len(magic)+8);if stat.Size()<footerSize{return bootstrap{},fmt.Errorf("customer bootstrap payload not found")};if _,err=f.Seek(-footerSize,io.SeekEnd);err!=nil{return bootstrap{},err};footer:=make([]byte,footerSize);if _,err=io.ReadFull(f,footer);err!=nil{return bootstrap{},err};if string(footer[8:])!=magic{return bootstrap{},fmt.Errorf("invalid customer bootstrap footer")};length:=binary.LittleEndian.Uint64(footer[:8]);if length==0||length>1024*1024||int64(length)+footerSize>stat.Size(){return bootstrap{},fmt.Errorf("invalid customer bootstrap length")};if _,err=f.Seek(-(footerSize+int64(length)),io.SeekEnd);err!=nil{return bootstrap{},err};payload:=make([]byte,length);if _,err=io.ReadFull(f,payload);err!=nil{return bootstrap{},err};var boot bootstrap;if err=json.Unmarshal(payload,&boot);err!=nil{return bootstrap{},fmt.Errorf("invalid customer bootstrap payload")};return boot,nil }
func download(url,dest string) error { client:=&http.Client{Timeout:2*time.Minute};resp,err:=client.Get(url);if err!=nil{return err};defer resp.Body.Close();if resp.StatusCode!=http.StatusOK{return fmt.Errorf("HTTP %d",resp.StatusCode)};f,err:=os.Create(dest);if err!=nil{return err};defer f.Close();_,err=io.Copy(f,resp.Body);return err }
func installerLogWriter() io.Writer { if installerLog != nil { return installerLog }; return io.Discard }
func fail(msg string){ logInstaller("ERROR: %s", msg); fmt.Fprintln(os.Stderr,"ERROR:",msg); os.Exit(1) }
