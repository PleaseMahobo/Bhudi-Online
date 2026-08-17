package main

import (
    "net/http"
    "net/url"
    "strings"
)

// agentAuthTransport binds enterprise agent callbacks to the credential issued
// during enrollment. Runtime enrollment itself is not modified.
type agentAuthTransport struct {
    base  http.RoundTripper
    token func() string
}

func (t agentAuthTransport) RoundTrip(req *http.Request) (*http.Response, error) {
    base := t.base
    if base == nil {
        base = http.DefaultTransport
    }
    if strings.Contains(req.URL.Path, "/api/v1/agent/") {
        token := strings.TrimSpace(t.token())
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

var _ http.RoundTripper = agentAuthTransport{}
var _ = url.Values{}
