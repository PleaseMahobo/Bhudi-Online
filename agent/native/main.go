package main

import (
	"flag"
	"fmt"
	"os"
	"strings"
)

const agentVersion = "2.4.0-service"

func main() {
	if len(os.Args) < 2 {
		runAgent(parseRunFlags(os.Args[1:]))
		return
	}
	switch strings.ToLower(os.Args[1]) {
	case "install":
		fs := flag.NewFlagSet("install", flag.ExitOnError)
		server := fs.String("server", envOr("BHUDI_SERVER_URL", defaultServerURL), "Bhudi backend base URL")
		_ = fs.Parse(os.Args[2:])
		if err := installService(strings.TrimRight(*server, "/")); err != nil {
			fatal(err)
		}
	case "uninstall":
		if err := uninstallService(); err != nil {
			fatal(err)
		}
	case "service":
		fs := flag.NewFlagSet("service", flag.ExitOnError)
		server := fs.String("server", envOr("BHUDI_SERVER_URL", defaultServerURL), "Bhudi backend base URL")
		_ = fs.Parse(os.Args[2:])
		if err := runWindowsService(strings.TrimRight(*server, "/")); err != nil {
			fatal(err)
		}
	case "run", "start":
		cfg := parseRunFlags(os.Args[2:])
		if isWindowsServiceProcess() {
			if err := runWindowsService(cfg.Server); err != nil {
				fatal(err)
			}
			return
		}
		runAgent(cfg)
	case "version", "-version", "--version":
		fmt.Println("bhudi-agent", agentVersion)
	case "help", "-h", "--help":
		fmt.Print(`Bhudi agent — install once, starts at every boot

  install -server URL   Install Windows Service / systemd / LaunchAgent
  uninstall             Remove service and startup entries
  service [-server URL] Run as a native Windows Service
  run [-server URL]     Run in foreground
  version

Windows (Administrator):
  bhudi-agent.exe install -server https://bhudi-online-production.up.railway.app

Linux (preferred with sudo for boot-wide service):
  sudo ./bhudi-agent-linux-amd64 install -server https://bhudi-online-production.up.railway.app
`)
	default:
		runAgent(parseRunFlags(os.Args[1:]))
	}
}

func parseRunFlags(args []string) runConfig {
	fs := flag.NewFlagSet("run", flag.ExitOnError)
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
