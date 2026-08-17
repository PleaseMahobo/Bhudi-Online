// Bhudi Agent Windows bootstrap installer.
// This executable is standalone: it does not require Python, Go, or any runtime.
package main

import (
    "flag"
    "fmt"
    "io"
    "net/http"
    "os"
    "os/exec"
    "path/filepath"
    "runtime"
    "strings"
)

const (
    defaultServer = "https://bhudi-online-production.up.railway.app"
    nativeURL = "https://github.com/PleaseMahobo/Bhudi-Online/releases/download/agent-native-latest/bhudi-agent-windows-amd64.exe"
)

func main() {
    if runtime.GOOS != "windows" { fail("This bootstrap installer is for Windows.") }
    server := flag.String("server", envOr("BHUDI_SERVER_URL", defaultServer), "Bhudi backend base URL")
    token := flag.String("enrollment-token", envOr("BHUDI_ENROLLMENT_TOKEN", ""), "single-use customer enrollment token")
    flag.Parse()
    *server = strings.TrimRight(strings.TrimSpace(*server), "/")
    *token = strings.TrimSpace(*token)
    if *token == "" { fail("A customer enrollment token is required. Generate one from the Bhudi customer portal.") }

    fmt.Println("========================================")
    fmt.Println("  Bhudi Agent Installer")
    fmt.Println("========================================")
    fmt.Println("Server:", *server)
    fmt.Println("Python: not required")

    tmp, err := os.MkdirTemp("", "bhudi-agent-setup-*")
    if err != nil { fail(err.Error()) }
    defer os.RemoveAll(tmp)
    binary := filepath.Join(tmp, "bhudi-agent.exe")

    fmt.Println("[1/2] Downloading signed native agent...")
    if err := download(nativeURL, binary); err != nil { fail("download: " + err.Error()) }

    fmt.Println("[2/2] Installing Windows service...")
    cmd := exec.Command(binary, "install", "-server", *server, "-enrollment-token", *token)
    cmd.Stdout = os.Stdout; cmd.Stderr = os.Stderr; cmd.Stdin = os.Stdin
    if err := cmd.Run(); err != nil { fail("agent installation failed: " + err.Error()) }
}

func envOr(k, def string) string { if v := strings.TrimSpace(os.Getenv(k)); v != "" { return v }; return def }
func download(url, dest string) error { resp,err:=http.Get(url);if err!=nil{return err};defer resp.Body.Close();if resp.StatusCode!=http.StatusOK{return fmt.Errorf("HTTP %d",resp.StatusCode)};f,err:=os.Create(dest);if err!=nil{return err};defer f.Close();_,err=io.Copy(f,resp.Body);return err }
func fail(msg string) { fmt.Fprintln(os.Stderr,"ERROR:",msg);os.Exit(1) }
