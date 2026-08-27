package main

import (
	"flag"
	"fmt"
	"os"
	"runtime"
	"strings"
)

// Set at link time: -ldflags "-X main.agentVersion=2.1.0"
var agentVersion = "2.1.0-dev"

func main() {
	if len(os.Args) < 2 {
		if runtime.GOOS == "windows" && isWindowsServiceProcess() {
			_ = runWindowsService(envOr("BHUDI_SERVER_URL", defaultServerURL))
			return
		}
		runAgent(parseRunFlags(nil))
		return
	}

	cmd := strings.ToLower(os.Args[1])
	switch cmd {
	case "enroll":
		cfg := parseRunFlags(os.Args[2:])
		ident, err := loadOrEnroll(cfg.Server)
		if err != nil {
			fatal(err)
		}
		fmt.Printf("enrolled agent_id=%s server=%s\n", ident.AgentID, cfg.Server)
	case "install":
		cfg := parseRunFlags(os.Args[2:])
		logInstall("install start version=%s os=%s/%s server=%s", agentVersion, runtime.GOOS, runtime.GOARCH, cfg.Server)
		if err := installService(cfg.Server); err != nil {
			logInstall("install FAILED: %v", err)
			fatal(err)
		}
		logInstall("install OK")
	case "upgrade":
		cfg := parseRunFlags(os.Args[2:])
		logInstall("upgrade start version=%s server=%s", agentVersion, cfg.Server)
		if err := upgradeService(cfg.Server); err != nil {
			logInstall("upgrade FAILED: %v", err)
			fatal(err)
		}
		logInstall("upgrade OK")
	case "uninstall":
		logInstall("uninstall start")
		if err := uninstallService(); err != nil {
			logInstall("uninstall FAILED: %v", err)
			fatal(err)
		}
		logInstall("uninstall OK")
	case "service":
		cfg := parseRunFlags(os.Args[2:])
		if err := runWindowsService(cfg.Server); err != nil {
			fatal(err)
		}
	case "run":
		runAgent(parseRunFlags(os.Args[2:]))
	case "version", "-v", "--version":
		fmt.Println("bhudi-agent", agentVersion)
	case "help", "-h", "--help":
		fmt.Print(`Bhudi Agent — enterprise RMM endpoint agent (native, no Python)

Commands:
  enroll   [-server URL]   Enroll and persist identity
  install  [-server URL]   Install as OS service (requires elevation on Windows)
  upgrade  [-server URL]   Replace binary & restart service (keeps identity)
  uninstall                Remove service, tasks, and startup entries
  service  [-server URL]   Run as native Windows Service (SCM entrypoint)
  run      [-server URL]   Foreground run (debug)
  version

Windows (Administrator):
  bhudi-agent.exe install -server https://api.example.com
  bhudi-agent.exe upgrade -server https://api.example.com
  bhudi-agent.exe uninstall

Linux (prefer sudo for boot-wide systemd unit):
  sudo ./bhudi-agent-linux-amd64 install -server https://api.example.com

macOS:
  sudo ./bhudi-agent-darwin-arm64 install -server https://api.example.com

Install log:
  Windows: %ProgramData%\Bhudi\Agent\install.log
  Linux:   /var/log/bhudi-agent-install.log (root) or ~/.local/share/bhudi-agent/install.log
  macOS:   ~/Library/Logs/Bhudi/install.log

MSI / enterprise deploy:
  Use bhudi-agent-setup.msi (per-machine, auto-start service) from the Bhudi portal or
  GitHub release tag agent-native-latest.
`)
	default:
		runAgent(parseRunFlags(os.Args[1:]))
	}
}

func parseRunFlags(args []string) runConfig {
	fs := flag.NewFlagSet("run", flag.ContinueOnError)
	fs.SetOutput(os.Stderr)
	server := fs.String("server", envOr("BHUDI_SERVER_URL", defaultServerURL), "server")
	interval := fs.Int("interval", 10, "heartbeat seconds")
	_ = fs.Parse(args)
	return runConfig{Server: strings.TrimRight(*server, "/"), Interval: *interval}
}

func fatal(err error) {
	fmt.Fprintln(os.Stderr, "error:", err)
	os.Exit(1)
}

func envOr(k, def string) string {
	if v := strings.TrimSpace(os.Getenv(k)); v != "" {
		return v
	}
	return def
}
