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
    agentURL = "https://github.com/PleaseMahobo/Bhudi-Online/releases/download/agent-native-latest/bhudi-agent.exe"
    supportURL = "https://github.com/PleaseMahobo/Bhudi-Online/releases/download/agent-native-latest/bhudi-support.exe"
    magic = "BHUDI_BOOTSTRAP_V1"
)

type bootstrap struct { ServerURL string `json:"server_url"`; EnrollmentToken string `json:"enrollment_token"` }

func main() {
    boot, err := readBootstrap(); if err != nil { fail("This is not a customer-specific Bhudi installer. Download a fresh installer from the Bhudi portal.\nDetails: "+err.Error()) }
    server := strings.TrimRight(strings.TrimSpace(boot.ServerURL), "/"); if server=="" {server=defaultServer}
    if strings.TrimSpace(boot.EnrollmentToken)=="" {fail("Customer enrollment information is missing. Download a fresh installer from the Bhudi portal.")}
    if runtime.GOOS!="windows" {fail("This installer is for Windows.")}
    fmt.Println("========================================");fmt.Println("  Bhudi Agent Setup");fmt.Println("========================================");fmt.Println("Customer enrollment: ready");fmt.Println("Server:",server)
    tmp,err:=os.MkdirTemp("","bhudi-setup-*");if err!=nil{fail(err.Error())};defer os.RemoveAll(tmp)
    agentPath:=filepath.Join(tmp,"bhudi-agent.exe");supportPath:=filepath.Join(tmp,"bhudi-support.exe")
    fmt.Println("[1/4] Downloading Bhudi agent...");if err=download(agentURL,agentPath);err!=nil{fail("agent download: "+err.Error())}
    fmt.Println("[2/4] Installing Windows service and enrolling endpoint...");cmd:=exec.Command(agentPath,"install","-server",server);cmd.Env=append(os.Environ(),"BHUDI_ENROLLMENT_TOKEN="+boot.EnrollmentToken);cmd.Stdout=os.Stdout;cmd.Stderr=os.Stderr;cmd.Stdin=os.Stdin;if err=cmd.Run();err!=nil{fail("agent installation failed: "+err.Error())}
    fmt.Println("Waiting for endpoint enrollment...");if err=waitForIdentity(90*time.Second);err!=nil{fail(err.Error())}
    fmt.Println("[3/4] Installing Bhudi Support Client...");if err=download(supportURL,supportPath);err!=nil{fail("support client download: "+err.Error())}
    installDir:=filepath.Join(os.Getenv("ProgramFiles"),"BhudiAgent");if err=os.MkdirAll(installDir,0755);err!=nil{fail("create support directory: "+err.Error())};installedSupport:=filepath.Join(installDir,"BhudiSupport.exe");if err=copyFile(supportPath,installedSupport);err!=nil{fail("install support client: "+err.Error())}
    _=exec.Command("reg","add",`HKCU\Software\Microsoft\Windows\CurrentVersion\Run`,"/v","BhudiSupport","/t","REG_SZ","/d",`"`+installedSupport+`"`,"/f").Run()
    _=exec.Command(installedSupport).Start()
    fmt.Println("[4/4] Installation complete");fmt.Println("Bhudi Support is available from the Windows system tray.");time.Sleep(2*time.Second)
}

func waitForIdentity(timeout time.Duration) error { deadline:=time.Now().Add(timeout);path:=filepath.Join(os.Getenv("ProgramData"),"Bhudi","Agent","agent_identity.json");for time.Now().Before(deadline){if st,err:=os.Stat(path);err==nil&&st.Size()>0{return nil};time.Sleep(2*time.Second)};return fmt.Errorf("agent enrollment did not complete within %s",timeout)}
func readBootstrap()(bootstrap,error){exe,err:=os.Executable();if err!=nil{return bootstrap{},err};f,err:=os.Open(exe);if err!=nil{return bootstrap{},err};defer f.Close();stat,err:=f.Stat();if err!=nil{return bootstrap{},err};footerSize:=int64(len(magic)+8);if stat.Size()<footerSize{return bootstrap{},fmt.Errorf("customer bootstrap payload not found")};if _,err=f.Seek(-footerSize,io.SeekEnd);err!=nil{return bootstrap{},err};footer:=make([]byte,footerSize);if _,err=io.ReadFull(f,footer);err!=nil{return bootstrap{},err};if string(footer[8:])!=magic{return bootstrap{},fmt.Errorf("invalid customer bootstrap footer")};length:=binary.LittleEndian.Uint64(footer[:8]);if length==0||length>1024*1024||int64(length)+footerSize>stat.Size(){return bootstrap{},fmt.Errorf("invalid customer bootstrap length")};if _,err=f.Seek(-(footerSize+int64(length)),io.SeekEnd);err!=nil{return bootstrap{},err};payload:=make([]byte,length);if _,err=io.ReadFull(f,payload);err!=nil{return bootstrap{},err};var boot bootstrap;if err=json.Unmarshal(payload,&boot);err!=nil{return bootstrap{},fmt.Errorf("invalid customer bootstrap payload")};return boot,nil}
func download(url,dest string)error{resp,err:=(&http.Client{Timeout:2*time.Minute}).Get(url);if err!=nil{return err};defer resp.Body.Close();if resp.StatusCode!=http.StatusOK{return fmt.Errorf("HTTP %d",resp.StatusCode)};f,err:=os.Create(dest);if err!=nil{return err};defer f.Close();_,err=io.Copy(f,resp.Body);return err}
func copyFile(src,dst string)error{in,err:=os.Open(src);if err!=nil{return err};defer in.Close();out,err:=os.Create(dst);if err!=nil{return err};defer out.Close();_,err=io.Copy(out,in);if err!=nil{return err};return out.Sync()}
func fail(msg string){fmt.Fprintln(os.Stderr,"ERROR:",msg);fmt.Println("Press Enter to exit...");_,_=fmt.Fscanln(os.Stdin);os.Exit(1)}
