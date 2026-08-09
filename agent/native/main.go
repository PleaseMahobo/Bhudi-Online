// Bhudi native agent — single static binary, no Python runtime required.
package main

import (
	"flag"
	"fmt"
	"os"
	"strings"
)

const agentVersion = "2.1.0-native-terminal"

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
		printHelp()
	default:
		runAgent(parseRunFlags(os.Args[1:]))
	}
}

func parseRunFlags(args []string) runConfig {
	fs := flag.NewFlagSet("run", flag.ExitOnError)
	server := fs.String("server", envOr("BHUDI_SERVER_URL", defaultServerURL), "Bhudi backend base URL")
	interval := fs.Int("interval", 10, "Heartbeat interval seconds")
	_ = fs.Parse(args)
	return runConfig{
		Server:   strings.TrimRight(*server, "/"),
		Interval: *interval,
	}
}

func printHelp() {
	fmt.Print(`Bhudi native agent (no Python required)

  bhudi-agent [run] [-server URL] [-interval N]   Run in foreground
  bhudi-agent install [-server URL]               Install service / startup task
  bhudi-agent uninstall                           Remove service / startup task
  bhudi-agent version

Supports interactive remote terminal sessions via WebSocket.

Environment:
  BHUDI_SERVER_URL    Backend base URL
  BHUDI_HOSTNAME      Override hostname
`)
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
