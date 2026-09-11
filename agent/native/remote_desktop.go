package main

import (
	"bytes"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"image"
	"image/jpeg"
	"runtime"
	"strings"
	"sync"
	"time"

	"github.com/gorilla/websocket"
)

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
			"session_id": sessionID, "streaming": true,
			"stream_path": "/api/v1/remote-access/sessions/" + sessionID + "/dashboard",
			"session_type": "desktop", "session_mode": sessionMode,
			"display_protocol": displayProtocol, "monitor_index": monitorIndex,
		},
	}
}

func runDesktopSession(wsURL, sessionID, sessionMode, displayProtocol string, monitorIndex int) {
	// SetThreadDesktop / BitBlt are OS-thread-affine. Without LockOSThread the
	// goroutine can migrate after attach and capture still sees Session 0.
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
	_ = writeJSON(conn, map[string]any{
		"type": "status", "session_id": sessionID, "status": "session_capture_diagnostics",
		"message": "Inspecting Windows interactive desktop", "diagnostics": desktopDiagnostics(),
	})

	if err := ensureInteractiveDesktop(); err != nil {
		_ = writeJSON(conn, map[string]any{
			"type": "error", "session_id": sessionID,
			"message": "screen capture unavailable: " + err.Error() + " (" + desktopStatusNote() + "). Log a user onto the console of this PC, then reconnect.",
			"diagnostics": desktopDiagnostics(),
		})
		fmt.Println("[remote-desktop] interactive desktop:", err, desktopStatusNote())
		return
	}
	fmt.Println("[remote-desktop] desktop status:", desktopStatusNote())
	_ = writeJSON(conn, map[string]any{
		"type": "status", "session_id": sessionID, "status": "session_capture_ready",
		"message": "Windows interactive desktop attached", "diagnostics": desktopDiagnostics(),
	})

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
	fmt.Printf("[remote-desktop] monitor=%d origin=(%d,%d) size=%dx%d count=%d version=%s\n",
		monitorIndex, ox, oy, fw, fh, len(mons), agentVersion)

	stop := make(chan struct{})
	var once sync.Once
	closeStop := func() { once.Do(func() { close(stop) }) }

	nativeW, nativeH := fw, fh
	frameW, frameH := fw, fh
	var frameMu sync.Mutex
	inputCh := make(chan map[string]any, 64)

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
						frameMu.Lock()
						fW, fH, nW, nH := frameW, frameH, nativeW, nativeH
						frameMu.Unlock()
						mapped := map[string]any{}
						for k, v := range inner {
							mapped[k] = v
						}
						fx, fy := numVal(inner["x"]), numVal(inner["y"])
						if fW > 0 && fH > 0 {
							fx = fx * float64(nW) / float64(fW)
							fy = fy * float64(nH) / float64(fH)
						}
						mapped["x"] = fx
						mapped["y"] = fy
						mapped["_ox"] = float64(ox)
						mapped["_oy"] = float64(oy)
						mapped["_nw"] = float64(nW)
						mapped["_nh"] = float64(nH)
						select {
						case inputCh <- mapped:
						default:
						}
					}
				}
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
		case ev := <-inputCh:
			_ = ensureInteractiveDesktop()
			nW := int(numVal(ev["_nw"]))
			nH := int(numVal(ev["_nh"]))
			oX := int(numVal(ev["_ox"]))
			oY := int(numVal(ev["_oy"]))
			if nW <= 0 {
				nW = nativeW
			}
			if nH <= 0 {
				nH = nativeH
			}
			applyDesktopInputAt(ev, nW, nH, oX, oY)
		case <-ticker.C:
			if err := ensureInteractiveDesktop(); err != nil {
				failStreak++
				if failStreak == 1 || failStreak%25 == 0 {
					fmt.Println("[remote-desktop] desktop attach:", err, desktopStatusNote())
					_ = writeJSON(conn, map[string]any{"type": "status", "session_id": sessionID, "status": "session_capture_attach_failed", "message": err.Error(), "diagnostics": desktopDiagnostics()})
				}
				continue
			}
			img, err := captureScreenRegion(monitorIndex)
			if err != nil {
				failStreak++
				if failStreak == 1 || failStreak%25 == 0 {
					fmt.Println("[remote-desktop] capture:", err, desktopStatusNote())
					_ = writeJSON(conn, map[string]any{"type": "status", "session_id": sessionID, "status": "session_capture_frame_failed", "message": err.Error(), "diagnostics": desktopDiagnostics()})
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
			frameMu.Lock()
			frameW, frameH = bw, bh
			frameMu.Unlock()
			seq++
			_ = writeJSON(conn, map[string]any{
				"type": "frame", "session_id": sessionID, "encoding": "jpeg", "seq": seq,
				"width": bw, "height": bh, "native_w": nativeW, "native_h": nativeH,
				"origin_x": ox, "origin_y": oy,
				"data": base64.StdEncoding.EncodeToString(buf.Bytes()),
			})
		}
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
