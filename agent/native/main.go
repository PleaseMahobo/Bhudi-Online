package main

import (
	"flag"
	"fmt"
	"os"
	"strings"
)

const agentVersion = "2.5.0-13b"

func main() {
	if len(os.Args) < 2 {
		runAgent(parseRunFlags(os.Args[1:]))
		return
	}
	switch strings.ToLower(os.Args[1]) {
	case "install":
		fs := flag.NewFlagSet("install", flag.ExitOnError)
		server := fs.String("server", envOr("BHUDI_SERVER_URL", defaultServerURL), "Bhudi backend base URL")
		enrollmentToken := fs.String("enrollment-token", envOr("BHUDI_ENROLLMENT_TOKEN", ""), "single-use customer enrollment token")
		_ = fs.Parse(os.Args[2:])
		if err := installService(strings.TrimRight(*server, "/"), strings.TrimSpace(*enrollmentToken)); err != nil {
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
		fmt.Print(`Bhudi agent — install once, starts at every boot

  install -server URL -enrollment-token TOKEN
  uninstall
  run [-server URL]
  version

Windows (Administrator):
  bhudi-agent.exe install -server https://your-backend.example.com -enrollment-token TOKEN

The enrollment token is single-use and tenant-bound. It is consumed by the
backend during first enrollment; the installed service stores only the issued
agent credential, not the enrollment token.
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
	return runConfig{Server: strings.TrimRight(*server, "/"), Interval: *interval, EnrollmentToken: strings.TrimSpace(envOr("BHUDI_ENROLLMENT_TOKEN", ""))}
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
