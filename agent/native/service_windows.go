//go:build windows

package main

import "golang.org/x/sys/windows/svc"

type bhudiWindowsService struct {
	server string
}

func (s *bhudiWindowsService) Execute(_ []string, req <-chan svc.ChangeRequest, status chan<- svc.Status) (bool, uint32) {
	const accepted = svc.AcceptStop | svc.AcceptShutdown
	status <- svc.Status{State: svc.StartPending}

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
