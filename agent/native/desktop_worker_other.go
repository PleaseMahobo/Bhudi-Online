//go:build !windows

package main

func launchDesktopWorker(serverURL, sessionID, sessionMode, displayProtocol string, monitorIndex int) error {
    go func() {
        wsURL, err := sessionWSURL(serverURL, sessionID, "")
        if err != nil {
            return
        }
        runDesktopSession(wsURL, sessionID, sessionMode, displayProtocol, monitorIndex)
    }()
    return nil
}

func desktopWorkerArgs(args []string) (runConfig, string, string, string, int, bool) {
    return runConfig{}, "", "", "", 0, false
}

func loadStoredIdentity() (identity, error) {
    return identity{}, nil
}
