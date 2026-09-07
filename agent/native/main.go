package main

import (
	"flag"
	"fmt"
	"os"
	"runtime"
	"strings"
)

// Set at link time: -ldflags "-X main.agentVersion=2.2.8"
var agentVersion = "2.2.8"

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
  upgrade  [-server URL]   Upgrade binary and service registration
  uninstall                Remove service and startup registration
  service  [-server URL]   Run as Windows service host
  run      [-server URL]   Foreground agent loop
  version                  Print version
`)
	default:
		fmt.Fprintf(os.Stderr, "unknown command: %s\n", cmd)
		os.Exit(2)
	}
}

func parseRunFlags(args []string) runConfig {
	fs := flag.NewFlagSet("bhudi-agent", flag.ContinueOnError)
	server := fs.String("server", envOr("BHUDI_SERVER_URL", defaultServerURL), "API base URL")
	interval := fs.Int("interval", 15, "heartbeat interval seconds")
	_ = fs.Parse(args)
	return runConfig{Server: strings.TrimRight(*server, "/"), Interval: *interval}
}

func envOr(k, def string) string {
	if v := os.Getenv(k); v != "" {
		return v
	}
	return def
}

func fatal(err error) {
	fmt.Fprintln(os.Stderr, err)
	os.Exit(1)
}
