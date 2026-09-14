//go:build windows

package main

import (
	"fmt"
	"time"

	"golang.org/x/sys/windows/svc"
)

type bhudiWindowsService struct {
	server string
}

func (s *bhudiWindowsService) Execute(_ []string, req <-chan svc.ChangeRequest, status chan<- svc.Status) (bool, uint32) {
	const accepted = svc.AcceptStop | svc.AcceptShutdown
	status <- svc.Status{State: svc.StartPending}

	// The management agent runs as LocalSystem, so start the optional support
	// tray explicitly inside the active user's WinSta0/default session. This
	// repairs endpoints installed before the tray startup changes and avoids
	// depending solely on a stale per-user Run key/task.
	if err := startSupportIfPresentFromService(); err != nil {
		fmt.Println("[support-client] startup deferred:", err)
	}

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

func startSupportIfPresentFromService() error {
	if err := startSupportIfPresent(serviceSupportDirectory()); err != nil {
		return err
	}
	// Give the interactive process a moment to initialize; no dependency is
	// introduced into the agent heartbeat/command loop.
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
