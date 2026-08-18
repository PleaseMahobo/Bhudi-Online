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
	agentURL      = "https://github.com/PleaseMahobo/Bhudi-Online/releases/download/agent-native-latest/bhudi-agent.exe"
	magic         = "BHUDI_BOOTSTRAP_V1"
)

type bootstrap struct {
	ServerURL       string `json:"server_url"`
	EnrollmentToken string `json:"enrollment_token"`
}

func main() {
	boot, err := readBootstrap()
	if err != nil {
		fail("This is not a customer-specific Bhudi installer. Download a fresh installer from the Bhudi portal.\nDetails: " + err.Error())
	}
	server := strings.TrimRight(strings.TrimSpace(boot.ServerURL), "/")
	if server == "" {
		server = defaultServer
	}
	if strings.TrimSpace(boot.EnrollmentToken) == "" {
		fail("Customer enrollment information is missing. Download a fresh installer from the Bhudi portal.")
	}
	if runtime.GOOS != "windows" {
		fail("This installer is for Windows.")
	}

	fmt.Println("========================================")
	fmt.Println("  Bhudi Agent Setup")
	fmt.Println("========================================")
	fmt.Println("Customer enrollment: ready")
	fmt.Println("Server:", server)

	tmp, err := os.MkdirTemp("", "bhudi-setup-*")
	if err != nil {
		fail(err.Error())
	}
	defer os.RemoveAll(tmp)

	agentPath := filepath.Join(tmp, "bhudi-agent.exe")
	fmt.Println("[1/3] Downloading Bhudi agent...")
	if err := download(agentURL, agentPath); err != nil {
		fail("agent download: " + err.Error())
	}

	fmt.Println("[2/3] Installing Windows service and enrolling endpoint...")
	cmd := exec.Command(agentPath, "install", "-server", server)
	cmd.Env = append(os.Environ(), "BHUDI_ENROLLMENT_TOKEN="+boot.EnrollmentToken)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	cmd.Stdin = os.Stdin
	if err := cmd.Run(); err != nil {
		fail("agent installation failed: " + err.Error())
	}

	fmt.Println("[3/3] Installation complete")
	fmt.Println("The agent will enroll automatically and appear in your customer portal.")
	time.Sleep(2 * time.Second)
}

func readBootstrap() (bootstrap, error) {
	exe, err := os.Executable()
	if err != nil {
		return bootstrap{}, err
	}
	f, err := os.Open(exe)
	if err != nil {
		return bootstrap{}, err
	}
	defer f.Close()
	stat, err := f.Stat()
	if err != nil {
		return bootstrap{}, err
	}
	footerSize := int64(len(magic) + 8)
	if stat.Size() < footerSize {
		return bootstrap{}, fmt.Errorf("customer bootstrap payload not found")
	}
	if _, err := f.Seek(-footerSize, io.SeekEnd); err != nil {
		return bootstrap{}, err
	}
	footer := make([]byte, footerSize)
	if _, err := io.ReadFull(f, footer); err != nil {
		return bootstrap{}, err
	}
	if string(footer[8:]) != magic {
		return bootstrap{}, fmt.Errorf("invalid customer bootstrap footer")
	}
	length := binary.LittleEndian.Uint64(footer[:8])
	if length == 0 || length > 1024*1024 || int64(length)+footerSize > stat.Size() {
		return bootstrap{}, fmt.Errorf("invalid customer bootstrap length")
	}
	if _, err := f.Seek(-(footerSize + int64(length)), io.SeekEnd); err != nil {
		return bootstrap{}, err
	}
	payload := make([]byte, length)
	if _, err := io.ReadFull(f, payload); err != nil {
		return bootstrap{}, err
	}
	var boot bootstrap
	if err := json.Unmarshal(payload, &boot); err != nil {
		return bootstrap{}, fmt.Errorf("invalid customer bootstrap payload")
	}
	return boot, nil
}

func download(url, dest string) error {
	client := &http.Client{Timeout: 2 * time.Minute}
	resp, err := client.Get(url)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("HTTP %d", resp.StatusCode)
	}
	f, err := os.Create(dest)
	if err != nil {
		return err
	}
	defer f.Close()
	_, err = io.Copy(f, resp.Body)
	return err
}

func fail(msg string) {
	fmt.Fprintln(os.Stderr, "ERROR:", msg)
	fmt.Println("Press Enter to exit...")
	_, _ = fmt.Fscanln(os.Stdin)
	os.Exit(1)
}
