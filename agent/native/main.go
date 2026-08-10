// Bhudi native agent — single static binary, no Python runtime required.
package main

import (
	"flag"
	"fmt"
	"os"
	"runtime"
	"strings"
)

const agentVersion = "2.3.0-session-capture"

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
	case "diagnose-capture", "diagnose":
		runCaptureDiagnose()
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

func runCaptureDiagnose() {
	fmt.Println("bhudi-agent", agentVersion, "capture diagnose")
	fmt.Println("  goos/goarch:", runtime.GOOS+"/"+runtime.GOARCH)
	fmt.Println("  desktop:    ", desktopStatusNote())
	if err := ensureInteractiveDesktop(); err != nil {
		fmt.Println("  attach:     FAIL —", err)
	} else {
		fmt.Println("  attach:     OK —", desktopStatusNote())
	}
	img, err := capturePrimaryScreen()
	if err != nil {
		fmt.Println("  capture:    FAIL —", err)
		fmt.Println()
		fmt.Println("Tips:")
		fmt.Println("  • Log on to the Windows console (not only RDP disconnect leaving Session 0).")
		fmt.Println("  • Run:  bhudi-agent.exe run -server <URL>   in that logged-on session.")
		fmt.Println("  • Reinstall with:  bhudi-agent.exe install -server <URL>")
		fmt.Println("    (creates an ONLOGON /IT interactive task so capture works after login).")
		os.Exit(1)
	}
	b := img.Bounds()
	fmt.Printf("  capture:    OK — %dx%d\n", b.Dx(), b.Dy())
	fmt.Println("Screen capture is configured for this session.")
}

func printHelp() {
	fmt.Print(`Bhudi native agent (no Python required)

  bhudi-agent [run] [-server URL] [-interval N]   Run in foreground
  bhudi-agent install [-server URL]               Install interactive logon task
  bhudi-agent uninstall                           Remove startup task
  bhudi-agent diagnose-capture                    Test WinSta0 desktop attach + GDI capture
  bhudi-agent version

Environment:
  BHUDI_SERVER_URL    Backend base URL
  BHUDI_HOSTNAME      Override hostname

Windows remote desktop capture needs an interactive console session.
Use "diagnose-capture" on the target PC to verify configuration.
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
