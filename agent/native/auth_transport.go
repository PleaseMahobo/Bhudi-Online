package main

import (
    "encoding/json"
    "net/http"
    "os"
    "strings"
)

type agentAuthTransport struct { base http.RoundTripper }

func (t agentAuthTransport) RoundTrip(req *http.Request) (*http.Response, error) {
    base := t.base
    if base == nil { base = http.DefaultTransport }
    if strings.Contains(req.URL.Path, "/api/v1/agent/") {
        token := ""
        if data, err := os.ReadFile(identityPath()); err == nil {
            var id identity
            if json.Unmarshal(data, &id) == nil { token = strings.TrimSpace(id.AgentToken) }
        }
        if token != "" {
            cloned := req.Clone(req.Context())
            q := cloned.URL.Query()
            q.Set("agent_token", token)
            cloned.URL.RawQuery = q.Encode()
            req = cloned
        }
    }
    return base.RoundTrip(req)
}

func init() {
    base := http.DefaultTransport
    http.DefaultTransport = agentAuthTransport{base: base}
}
