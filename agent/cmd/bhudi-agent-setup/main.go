// Bhudi Agent Windows setup bootstrap (real .exe installer).
// Cross-compile:
//   GOOS=windows GOARCH=amd64 CGO_ENABLED=0 go build -ldflags="-s -w" -o bhudi-agent-setup.exe .
package main

import (
	"archive/zip"
	"flag"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"
)

const (
	defaultServer = "https://bhudi-online-production.up.railway.app"
	repoZipURL    = "https://github.com/PleaseMahobo/Bhudi-Online/archive/refs/heads/main.zip"
	taskName      = "BhudiAgent"
)

func main() {
	server := flag.String("server", envOr("BHUDI_SERVER_URL", defaultServer), "Bhudi backend base URL")
	installDir := flag.String("dir", "", "Install directory")
	skipTask := flag.Bool("skip-task", false, "Do not register Scheduled Task")
	flag.Parse()

	*server = strings.TrimRight(strings.TrimSpace(*server), "/")
	fmt.Println("========================================")
	fmt.Println("  Bhudi Agent Setup")
	fmt.Println("========================================")
	fmt.Println("Server:", *server)

	dir := *installDir
	if dir == "" {
		if pf := os.Getenv("ProgramFiles"); pf != "" && canWrite(filepath.Join(pf, "BhudiAgent-test")) {
			dir = filepath.Join(pf, "BhudiAgent")
		} else if la := os.Getenv("LOCALAPPDATA"); la != "" {
			dir = filepath.Join(la, "BhudiAgent")
		} else {
			dir = filepath.Join(".", "BhudiAgent")
		}
	}
	fmt.Println("Install:", dir)

	python, err := findPython()
	if err != nil {
		fail("Python 3.10+ is required. Install from https://www.python.org/downloads/ (enable Add to PATH), then re-run this setup.\nDetails: " + err.Error())
	}
	fmt.Println("Python:", python)

	tmp, err := os.MkdirTemp("", "bhudi-setup-*")
	if err != nil {
		fail(err.Error())
	}
	defer os.RemoveAll(tmp)

	zipPath := filepath.Join(tmp, "repo.zip")
	fmt.Println("[1/5] Downloading agent package...")
	if err := download(repoZipURL, zipPath); err != nil {
		fail("download: " + err.Error())
	}

	fmt.Println("[2/5] Extracting...")
	extractRoot := filepath.Join(tmp, "src")
	if err := unzip(zipPath, extractRoot); err != nil {
		fail("extract: " + err.Error())
	}
	agentSrc, err := findAgentDir(extractRoot)
	if err != nil {
		fail(err.Error())
	}

	fmt.Println("[3/5] Installing files to", dir)
	if err := os.MkdirAll(dir, 0755); err != nil {
		fail(err.Error())
	}
	if err := copyDir(agentSrc, dir); err != nil {
		fail("copy: " + err.Error())
	}
	cfg := fmt.Sprintf("{\n  \"server_url\": %q,\n  \"heartbeat_interval\": 10\n}\n", *server)
	if err := os.WriteFile(filepath.Join(dir, "agent_config.json"), []byte(cfg), 0644); err != nil {
		fail(err.Error())
	}

	venv := filepath.Join(dir, ".venv")
	venvPython := filepath.Join(venv, "Scripts", "python.exe")
	fmt.Println("[4/5] Creating virtual environment and installing dependencies...")
	if err := run(python, "-m", "venv", venv); err != nil {
		fail("venv: " + err.Error())
	}
	_ = run(venvPython, "-m", "pip", "install", "--upgrade", "pip")
	if err := run(venvPython, "-m", "pip", "install", "-r", filepath.Join(dir, "requirements.txt")); err != nil {
		fail("pip: " + err.Error())
	}

	runner := filepath.Join(dir, "run-agent.bat")
	bat := fmt.Sprintf("@echo off\r\nset BHUDI_SERVER_URL=%s\r\ncd /d \"%s\"\r\n\"%s\" main.py\r\n", *server, dir, venvPython)
	if err := os.WriteFile(runner, []byte(bat), 0644); err != nil {
		fail(err.Error())
	}

	fmt.Println("[5/5] Registering startup task...")
	if !*skipTask {
		_ = exec.Command("schtasks", "/Delete", "/TN", taskName, "/F").Run()
		create := exec.Command("schtasks", "/Create", "/TN", taskName, "/TR", runner, "/SC", "ONLOGON", "/RL", "HIGHEST", "/F")
		if out, err := create.CombinedOutput(); err != nil {
			fmt.Println("Warning: scheduled task not created:", string(out), err)
		} else {
			fmt.Println("Scheduled task:", taskName)
		}
		_ = exec.Command("schtasks", "/Run", "/TN", taskName).Start()
	}

	cmd := exec.Command("cmd", "/C", "start", "", runner)
	_ = cmd.Start()

	fmt.Println()
	fmt.Println("Bhudi Agent installed successfully.")
	fmt.Println("  Directory:", dir)
	fmt.Println("  Server:   ", *server)
	fmt.Println("  Runner:   ", runner)
	fmt.Println()
	fmt.Println("The agent will enroll on first heartbeat and appear under Devices.")
	fmt.Println("You can close this window.")
	time.Sleep(3 * time.Second)
}

func envOr(k, def string) string {
	if v := strings.TrimSpace(os.Getenv(k)); v != "" {
		return v
	}
	return def
}

func canWrite(testPath string) bool {
	if err := os.MkdirAll(filepath.Dir(testPath), 0755); err != nil {
		return false
	}
	f, err := os.Create(testPath)
	if err != nil {
		return false
	}
	f.Close()
	os.Remove(testPath)
	return true
}

func findPython() (string, error) {
	candidates := [][]string{{"py", "-3"}, {"python"}, {"python3"}}
	for _, c := range candidates {
		cmd := exec.Command(c[0], append(c[1:], "-c", "import sys; print(sys.executable)")...)
		out, err := cmd.Output()
		if err == nil {
			p := strings.TrimSpace(string(out))
			if p != "" {
				return p, nil
			}
		}
	}
	return "", fmt.Errorf("python not found on PATH")
}

func download(url, dest string) error {
	resp, err := http.Get(url)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode != 200 {
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

func unzip(src, dest string) error {
	r, err := zip.OpenReader(src)
	if err != nil {
		return err
	}
	defer r.Close()
	for _, f := range r.File {
		fp := filepath.Join(dest, f.Name)
		if !strings.HasPrefix(filepath.Clean(fp), filepath.Clean(dest)+string(os.PathSeparator)) {
			return fmt.Errorf("illegal path in zip")
		}
		if f.FileInfo().IsDir() {
			_ = os.MkdirAll(fp, 0755)
			continue
		}
		if err := os.MkdirAll(filepath.Dir(fp), 0755); err != nil {
			return err
		}
		rc, err := f.Open()
		if err != nil {
			return err
		}
		out, err := os.OpenFile(fp, os.O_CREATE|os.O_RDWR|os.O_TRUNC, f.Mode())
		if err != nil {
			rc.Close()
			return err
		}
		_, err = io.Copy(out, rc)
		out.Close()
		rc.Close()
		if err != nil {
			return err
		}
	}
	return nil
}

func findAgentDir(root string) (string, error) {
	var found string
	_ = filepath.Walk(root, func(path string, info os.FileInfo, err error) error {
		if err != nil || found != "" {
			return nil
		}
		if info.Name() == "main.py" && strings.Contains(path, "agent") {
			found = filepath.Dir(path)
			return io.EOF
		}
		return nil
	})
	if found == "" {
		return "", fmt.Errorf("agent/main.py not found in package")
	}
	return found, nil
}

func copyDir(src, dst string) error {
	return filepath.Walk(src, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		rel, err := filepath.Rel(src, path)
		if err != nil {
			return err
		}
		target := filepath.Join(dst, rel)
		if info.IsDir() {
			return os.MkdirAll(target, 0755)
		}
		return copyFile(path, target)
	})
}

func copyFile(src, dst string) error {
	in, err := os.Open(src)
	if err != nil {
		return err
	}
	defer in.Close()
	if err := os.MkdirAll(filepath.Dir(dst), 0755); err != nil {
		return err
	}
	out, err := os.OpenFile(dst, os.O_CREATE|os.O_WRONLY|os.O_TRUNC, 0644)
	if err != nil {
		return err
	}
	defer out.Close()
	_, err = io.Copy(out, in)
	return err
}

func run(name string, args ...string) error {
	cmd := exec.Command(name, args...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	return cmd.Run()
}

func fail(msg string) {
	fmt.Fprintln(os.Stderr, "ERROR:", msg)
	fmt.Println("Press Enter to exit...")
	_, _ = fmt.Scanln()
	os.Exit(1)
}
