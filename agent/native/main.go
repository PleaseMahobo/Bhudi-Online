package main

import (
	"flag"
	"fmt"
	"os"
	"strings"
)

const agentVersion = "2.3.0-persist"

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
	case "run", "start":
		runAgent(parseRunFlags(os.Args[2:]))
	case "version", "-version", "--version":
		fmt.Println("bhudi-agent", agentVersion)
	case "help", "-h", "--help":
		fmt.Print(`Bhudi agent — install once, stays online

  install -server URL   Install + logon task + 5-min watchdog
  uninstall             Remove tasks and startup entry
  run [-server URL]     Run in foreground (used by tasks)
  version

Designed for personal PCs as well as managed fleets.
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
