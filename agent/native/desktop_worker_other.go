//go:build !windows

package main

func launchDesktopWorker(serverURL, sessionID, sessionMode, displayProtocol string, monitorIndex int, inputToken string) error {
    go func() {
        wsURL, err := sessionWSURL(serverURL, sessionID, "")
        if err != nil {
            return
        }
        runDesktopSession(wsURL, sessionID, sessionMode, displayProtocol, monitorIndex, inputToken)
    }()
    return nil
}

func desktopWorkerArgs(args []string) (runConfig, string, string, string, int, string, bool) {
    return runConfig{}, "", "", "", 0, "", false
}

func loadStoredIdentity() (identity, error) {
    return identity{}, nil
}
