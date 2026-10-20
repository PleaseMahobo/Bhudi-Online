//go:build windows

package main

import (
	"fmt"
	"os/exec"
	"strings"
	"time"

	"golang.org/x/sys/windows/svc"
)

type bhudiWindowsService struct {
	server string
}

func (s *bhudiWindowsService) Execute(_ []string, req <-chan svc.ChangeRequest, status chan<- svc.Status) (bool, uint32) {
	const accepted = svc.AcceptStop | svc.AcceptShutdown
	status <- svc.Status{State: svc.StartPending}

	// The service can start before a user logs on. Keep tray startup separate
	// from the heartbeat/command loop and retry until an interactive session is
	// available. startSupportIfPresent uses the active user's WinSta0/default
	// session, so the tray is visible to the logged-on user instead of Session 0.
	go ensureSupportTrayFromService()

	go runAgent(runConfig{Server: s.server, Interval: 10})
	status <- svc.Status{State: svc.Running, Accepts: accepted}

	for c := range req {
		switch c.Cmd {
		case svc.Interrogate:
			status <- svc.Status{State: svc.Running, Accepts: accepted}
		case svc.Stop, svc.Shutdown:
			status <- svc.Status{State: svc.StopPending}
			return false, 0
		}
	}
	return false, 0
}

func ensureSupportTrayFromService() {
	const retryInterval = 5 * time.Second
	for {
		if supportProcessRunning() {
			return
		}
		if err := startSupportIfPresentFromService(); err != nil {
			fmt.Println("[support-client] startup deferred:", err)
		}
		time.Sleep(retryInterval)
	}
}

func supportProcessRunning() bool {
	out, err := exec.Command("tasklist", "/FI", "IMAGENAME eq "+supportExeName, "/FO", "CSV", "/NH").CombinedOutput()
	if err != nil {
		return false
	}
	text := strings.TrimSpace(string(out))
	return text != "" && !strings.Contains(strings.ToLower(text), "no tasks are running")
}

func startSupportIfPresentFromService() error {
	if err := startSupportIfPresent(serviceSupportDirectory()); err != nil {
		return err
	}
	// Do not block the agent loop; the child runs independently in the user's
	// interactive session.
	time.Sleep(250 * time.Millisecond)
	return nil
}

func serviceSupportDirectory() string {
	if pd := envOr("ProgramData", ""); pd != "" {
		return pd + "\\Bhudi\\Agent"
	}
	if pf := envOr("ProgramFiles", ""); pf != "" {
		return pf + "\\Bhudi\\Agent"
	}
	return "."
}

func runWindowsService(server string) error {
	if server == "" {
		server = defaultServerURL
	}
	return svc.Run(windowsServiceName, &bhudiWindowsService{server: server})
}

func isWindowsServiceProcess() bool {
	ok, err := svc.IsWindowsService()
	return err == nil && ok
}
