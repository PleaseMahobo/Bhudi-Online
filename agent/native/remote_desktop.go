package main

import (
	"bytes"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"image/jpeg"
	"runtime"
	"strings"
	"sync"
	"time"

	"github.com/gorilla/websocket"
)

// startRemoteDesktop streams screen frames over the remote-access WebSocket session.
func startRemoteDesktop(serverURL, agentID string, command map[string]any) map[string]any {
	payload, _ := command["payload"].(map[string]any)
	if payload == nil {
		payload = map[string]any{}
	}
	sessionID := strVal(payload["session_id"])
	if sessionID == "" {
		return resultErr("session_id is required for screen sharing")
	}

	sessionMode := strings.ToLower(strVal(payload["session_mode"]))
	if sessionMode == "" {
		sessionMode = "control"
	}
	displayProtocol := strVal(payload["display_protocol"])
	if displayProtocol == "" {
		displayProtocol = "native"
	}
	monitorIndex := 0
	if v, ok := payload["monitor_index"]; ok {
		switch n := v.(type) {
		case float64:
			monitorIndex = int(n)
		case int:
			monitorIndex = n
		}
	}

	wsURL, err := sessionWSURL(serverURL, sessionID, agentID)
	if err != nil {
		return resultErr(err.Error())
	}

	go runDesktopSession(wsURL, sessionID, sessionMode, displayProtocol, monitorIndex)

	return map[string]any{
		"exit_code": 0,
		"stdout":    "started remote desktop session " + sessionID,
		"stderr":    "",
		"metadata": map[string]any{
			"session_id":       sessionID,
			"streaming":        true,
			"stream_path":      "/api/v1/remote-access/sessions/" + sessionID + "/dashboard",
			"session_type":     "desktop",
			"session_mode":     sessionMode,
			"display_protocol": displayProtocol,
			"monitor_index":    monitorIndex,
		},
	}
}

func runDesktopSession(wsURL, sessionID, sessionMode, displayProtocol string, monitorIndex int) {
	fmt.Println("[remote-desktop] connecting", wsURL, "monitor", monitorIndex)
	dialer := websocket.Dialer{HandshakeTimeout: 20 * time.Second}
	conn, resp, err := dialer.Dial(wsURL, nil)
	if err != nil {
		status := 0
		if resp != nil {
			status = resp.StatusCode
		}
		fmt.Printf("[remote-desktop] dial failed status=%d err=%v\n", status, err)
		return
	}
	defer conn.Close()

	_ = conn.SetReadDeadline(time.Now().Add(30 * time.Second))
	_, msg, err := conn.ReadMessage()
	if err != nil {
		fmt.Println("[remote-desktop] read attach:", err)
		return
	}
	fmt.Println("[remote-desktop] attached:", string(msg)[:min(120, len(msg))])
	_ = conn.SetReadDeadline(time.Time{})

	ox, oy, fw, fh, err := monitorRect(monitorIndex)
	if err != nil {
		_ = writeJSON(conn, map[string]any{
			"type": "error", "session_id": sessionID,
			"message": "screen capture unavailable: " + err.Error(),
		})
		fmt.Println("[remote-desktop] capture unavailable:", err)
		return
	}
	mons := listMonitors()

	_ = writeJSON(conn, map[string]any{
		"type":             "desktop_ready",
		"session_id":       sessionID,
		"platform":         runtime.GOOS,
		"display_protocol": displayProtocol,
		"session_mode":     sessionMode,
		"width":            fw,
		"height":           fh,
		"monitor_index":    monitorIndex,
		"origin_x":         ox,
		"origin_y":         oy,
		"encoding":         "jpeg",
		"monitors":         mons,
	})

	stop := make(chan struct{})
	var once sync.Once
	closeStop := func() { once.Do(func() { close(stop) }) }

	go func() {
		defer closeStop()
		for {
			_, raw, err := conn.ReadMessage()
			if err != nil {
				return
			}
			var message map[string]any
			if json.Unmarshal(raw, &message) != nil {
				continue
			}
			msgType := strVal(message["type"])
			if msgType == "session_attached" {
				continue
			}
			if msgType == "dashboard_message" {
				inner, _ := message["payload"].(map[string]any)
				if inner == nil {
					continue
				}
				ev := strVal(inner["type"])
				switch ev {
				case "close":
					_ = writeJSON(conn, map[string]any{
						"type": "session_closed", "session_id": sessionID, "reason": "closed_by_operator",
					})
					return
				case "mouse", "mousemove", "mousedown", "mouseup", "click", "wheel",
					"keydown", "keyup", "keypress", "keyboard":
					if sessionMode == "control" {
						applyDesktopInputAt(inner, fw, fh, ox, oy)
					}
				default:
					// ignore unknown
				}
			}
			if msgType == "close" {
				return
			}
		}
	}()

	ticker := time.NewTicker(350 * time.Millisecond)
	defer ticker.Stop()
	seq := 0
	for {
		select {
		case <-stop:
			fmt.Println("[remote-desktop] session ended", sessionID)
			return
		case <-ticker.C:
			img, err := captureScreenRegion(monitorIndex)
			if err != nil {
				fmt.Println("[remote-desktop] capture:", err)
				continue
			}
			img = maybeScale(img, 1280)
			var buf bytes.Buffer
			if err := jpeg.Encode(&buf, img, &jpeg.Options{Quality: 55}); err != nil {
				continue
			}
			seq++
			_ = writeJSON(conn, map[string]any{
				"type":       "frame",
				"session_id": sessionID,
				"encoding":   "jpeg",
				"seq":        seq,
				"width":      img.Bounds().Dx(),
				"height":     img.Bounds().Dy(),
				"data":       base64.StdEncoding.EncodeToString(buf.Bytes()),
			})
		}
	}
}

func maybeScale(img interface{ Bounds() interface{ Dx() int; Dy() int } }, maxWidth int) interface{} {
	return maybeScaleImg(img, maxWidth)
}
