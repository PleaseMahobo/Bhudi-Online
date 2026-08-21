//go:build windows

package main

import (
	"context"
	"fmt"

	"golang.org/x/sys/windows/svc"
)

type bhudiWindowsService struct {
	server string
	cancel context.CancelFunc
	done   chan struct{}
}

func (s *bhudiWindowsService) Execute(_ []string, req <-chan svc.ChangeRequest, status chan<- svc.Status) (bool, uint32) {
	const accepted = svc.AcceptStop | svc.AcceptShutdown
	status <- svc.Status{State: svc.StartPending}

	ctx, cancel := context.WithCancel(context.Background())
	s.cancel = cancel
	s.done = make(chan struct{})
	go func() {
		defer close(s.done)
		runAgent(ctx, runConfig{Server: s.server, Interval: 10})
	}()

	status <- svc.Status{State: svc.Running, Accepts: accepted}
	for c := range req {
		switch c.Cmd {
		case svc.Interrogate:
			status <- svc.Status{State: svc.Running, Accepts: accepted}
		case svc.Stop, svc.Shutdown:
			status <- svc.Status{State: svc.StopPending}
			cancel()
			<-s.done
			return false, 0
		default:
			return false, uint32(svc.StopReasonOther)
		}
	}
	cancel()
	<-s.done
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
	if err != nil {
		return false
	}
	return ok
}

func serviceFatal(err error) {
	if err != nil {
		fatal(fmt.Errorf("windows service: %w", err))
	}
}
