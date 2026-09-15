package main

import (
	"bytes"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"image"
	"image/jpeg"
	"net/url"
	"runtime"
	"strings"
	"sync"
	"time"

	"github.com/gorilla/websocket"
)

type desktopInputTiming struct {
	mu                 sync.RWMutex
	lastEventID        string
	lastWindowsInputAt int64
}

func (t *desktopInputTiming) set(eventID string, windowsInputAt int64) {
	t.mu.Lock()
	t.lastEventID = eventID
	t.lastWindowsInputAt = windowsInputAt
	t.mu.Unlock()
}

func (t *desktopInputTiming) get() (string, int64) {
	t.mu.RLock()
	defer t.mu.RUnlock()
	return t.lastEventID, t.lastWindowsInputAt
}

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
	inputToken := strVal(payload["input_token"])
	if sessionMode == "control" && inputToken == "" {
		return resultErr("input_token is required for interactive remote desktop")
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

	if runtime.GOOS == "windows" && isWindowsServiceProcess() {
		if err := launchDesktopWorker(serverURL, sessionID, sessionMode, displayProtocol, monitorIndex, inputToken); err != nil {
			return resultErr("failed to launch interactive desktop worker: " + err.Error())
		}
		return map[string]any{
			"exit_code": 0,
			"stdout":    "launched interactive remote desktop worker " + sessionID,
			"stderr":    "",
			"metadata": map[string]any{
				"session_id": sessionID, "streaming": true,
				"stream_path": "/api/v1/remote-access/sessions/" + sessionID + "/dashboard",
				"input_stream_path": "/api/v1/remote-access/sessions/" + sessionID + "/dashboard?channel=input",
				"session_type": "desktop", "session_mode": sessionMode,
				"display_protocol": displayProtocol, "monitor_index": monitorIndex,
			},
		}
	}

	go runDesktopSession(wsURL, sessionID, sessionMode, displayProtocol, monitorIndex, inputToken)
	return map[string]any{
		"exit_code": 0,
		"stdout":    "started remote desktop session " + sessionID,
		"stderr":    "",
		"metadata": map[string]any{
			"session_id": sessionID, "streaming": true,
			"stream_path": "/api/v1/remote-access/sessions/" + sessionID + "/dashboard",
			"input_stream_path": "/api/v1/remote-access/sessions/" + sessionID + "/dashboard?channel=input",
			"session_type": "desktop", "session_mode": sessionMode,
			"display_protocol": displayProtocol, "monitor_index": monitorIndex,
		},
	}
}

func inputWSURL(wsURL, token string) string {
	if token == "" {
		return wsURL
	}
	return wsURL + "?channel=input&token=" + url.QueryEscape(token)
}

func runDesktopSession(wsURL, sessionID, sessionMode, displayProtocol string, monitorIndex int, inputToken string) {
	runtime.LockOSThread()
	defer runtime.UnlockOSThread()

	fmt.Println("[remote-desktop] connecting", wsURL, "monitor", monitorIndex, "console", activeConsoleSessionID())
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

	if err := ensureInteractiveDesktop(); err != nil {
		_ = writeJSON(conn, map[string]any{
			"type": "error", "session_id": sessionID,
			"message": "screen capture unavailable: " + err.Error() + " (" + desktopStatusNote() + "). Log a user onto the console of this PC, then reconnect.",
		})
		fmt.Println("[remote-desktop] interactive desktop:", err, desktopStatusNote())
		return
	}
	fmt.Println("[remote-desktop] desktop status:", desktopStatusNote())

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
		"type": "desktop_ready", "session_id": sessionID,
		"platform": runtime.GOOS, "display_protocol": displayProtocol,
		"session_mode": sessionMode, "width": fw, "height": fh,
		"native_w": fw, "native_h": fh,
		"monitor_index": monitorIndex, "origin_x": ox, "origin_y": oy,
		"encoding": "jpeg", "monitors": mons,
		"agent_version": agentVersion, "console_session": activeConsoleSessionID(),
	})
	fmt.Printf("[remote-desktop] monitor=%d origin=(%d,%d) size=%dx%d count=%d version=%s\n", monitorIndex, ox, oy, fw, fh, len(mons), agentVersion)

	stop := make(chan struct{})
	var once sync.Once
	closeStop := func() { once.Do(func() { close(stop) }) }

	nativeW, nativeH := fw, fh
	inputTiming := &desktopInputTiming{}

	if sessionMode == "control" {
		go runDesktopInputChannel(inputWSURL(wsURL, inputToken), sessionID, inputToken, nativeW, nativeH, ox, oy, inputTiming, closeStop)
	}

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
			if msgType == "session_attached" || msgType == "input_channel_ready" {
				continue
			}
			if msgType == "close" {
				return
			}
		}
	}()

	ticker := time.NewTicker(200 * time.Millisecond)
	defer ticker.Stop()
	seq := 0
	failStreak := 0
	for {
		select {
		case <-stop:
			fmt.Println("[remote-desktop] session ended", sessionID)
			return
		case <-ticker.C:
			img, err := captureScreenRegion(monitorIndex)
			if err != nil {
				failStreak++
				if failStreak == 1 || failStreak%25 == 0 {
					fmt.Println("[remote-desktop] capture:", err, desktopStatusNote())
				}
				continue
			}
			failStreak = 0
			img = maybeScale(img, 1600)
			var buf bytes.Buffer
			if err := jpeg.Encode(&buf, img, &jpeg.Options{Quality: 55}); err != nil {
				continue
			}
			bw, bh := img.Bounds().Dx(), img.Bounds().Dy()
			seq++
			frame := map[string]any{
				"type": "frame", "session_id": sessionID, "encoding": "jpeg", "seq": seq,
				"width": bw, "height": bh, "native_w": nativeW, "native_h": nativeH,
				"origin_x": ox, "origin_y": oy,
				"frame_sent_at_ms": time.Now().UnixMilli(),
				"data": base64.StdEncoding.EncodeToString(buf.Bytes()),
			}
			if eventID, windowsInputAt := inputTiming.get(); eventID != "" {
				frame["input_event_id"] = eventID
				frame["windows_input_at_ms"] = windowsInputAt
			}
			_ = writeJSON(conn, frame)
		}
	}
}

func runDesktopInputChannel(wsURL, sessionID, inputToken string, frameW, frameH, originX, originY int, timing *desktopInputTiming, closeSession func()) {
	runtime.LockOSThread()
	defer runtime.UnlockOSThread()

	dialer := websocket.Dialer{HandshakeTimeout: 20 * time.Second}
	conn, resp, err := dialer.Dial(wsURL, nil)
	if err != nil {
		status := 0
		if resp != nil {
			status = resp.StatusCode
		}
		fmt.Printf("[remote-desktop-input] dial failed status=%d err=%v\n", status, err)
		closeSession()
		return
	}
	defer conn.Close()
	_ = conn.SetReadDeadline(time.Now().Add(30 * time.Second))
	_, attach, err := conn.ReadMessage()
	if err != nil {
		fmt.Println("[remote-desktop-input] read attach:", err)
		closeSession()
		return
	}
	fmt.Println("[remote-desktop-input] authenticated attach:", string(attach)[:min(160, len(attach))])
	_ = conn.SetReadDeadline(time.Time{})

	if err := ensureInteractiveDesktop(); err != nil {
		_ = writeJSON(conn, map[string]any{
			"type": "input_error", "session_id": sessionID,
			"message": "interactive desktop unavailable: " + err.Error(),
			"agent_received_at_ms": time.Now().UnixMilli(),
		})
		closeSession()
		return
	}

	for {
		_, raw, err := conn.ReadMessage()
		if err != nil {
			closeSession()
			return
		}
		var envelope map[string]any
		if json.Unmarshal(raw, &envelope) != nil {
			continue
		}
		if strVal(envelope["type"]) == "close" {
			closeSession()
			return
		}
		if strVal(envelope["type"]) != "input" {
			continue
		}
		ev, _ := envelope["payload"].(map[string]any)
		if ev == nil {
			continue
		}
		eventID := strVal(ev["event_id"])
		agentReceivedAt := time.Now().UnixMilli()
		ev["agent_received_at_ms"] = agentReceivedAt
		ev["_nw"] = float64(frameW)
		ev["_nh"] = float64(frameH)
		ev["_ox"] = float64(originX)
		ev["_oy"] = float64(originY)
		applyDesktopInputAt(ev, frameW, frameH, originX, originY)
		windowsInputAt := time.Now().UnixMilli()
		timing.set(eventID, windowsInputAt)
		ack := map[string]any{
			"type": "input_ack",
			"session_id": sessionID,
			"event_id": eventID,
			"browser_sent_at_ms": ev["browser_sent_at_ms"],
			"backend_received_at_ms": ev["backend_received_at_ms"],
			"agent_received_at_ms": agentReceivedAt,
			"windows_input_at_ms": windowsInputAt,
			"ack_sent_at_ms": time.Now().UnixMilli(),
			"input_type": strVal(ev["type"]),
		}
		if err := writeJSON(conn, ack); err != nil {
			closeSession()
			return
		}
		_ = inputToken
	}
}

func maybeScale(img image.Image, maxWidth int) image.Image {
	b := img.Bounds()
	w, h := b.Dx(), b.Dy()
	if w <= maxWidth {
		return img
	}
	nw := maxWidth
	nh := h * maxWidth / w
	dst := image.NewRGBA(image.Rect(0, 0, nw, nh))
	for y := 0; y < nh; y++ {
		sy := y * h / nh
		for x := 0; x < nw; x++ {
			sx := x * w / nw
			dst.Set(x, y, img.At(b.Min.X+sx, b.Min.Y+sy))
		}
	}
	return dst
}
