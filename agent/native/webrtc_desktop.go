package main

import (
	"encoding/json"
	"fmt"
	"time"

	"github.com/gorilla/websocket"
	"github.com/pion/webrtc/v4"
)

// startRemoteDesktopWebRTC starts a Pion peer and signals over the session WebSocket.
func startRemoteDesktopWebRTC(serverURL, agentID string, command map[string]any) map[string]any {
	payload, _ := command["payload"].(map[string]any)
	if payload == nil {
		payload = map[string]any{}
	}
	sessionID := strVal(payload["session_id"])
	if sessionID == "" {
		return resultErr("session_id is required for webrtc desktop")
	}
	wsURL, err := sessionWSURL(serverURL, sessionID, agentID)
	if err != nil {
		return resultErr(err.Error())
	}
	go runWebRTCDesktopSession(wsURL, sessionID)
	return map[string]any{
		"exit_code": 0,
		"stdout":    "started webrtc desktop session " + sessionID,
		"stderr":    "",
		"metadata": map[string]any{
			"session_id":  sessionID,
			"streaming":   true,
			"transport":   "webrtc",
			"stream_path": "/api/v1/remote-access/sessions/" + sessionID + "/dashboard",
		},
	}
}

func runWebRTCDesktopSession(wsURL, sessionID string) {
	fmt.Println("[webrtc-desktop] connecting", wsURL)
	dialer := websocket.Dialer{HandshakeTimeout: 20 * time.Second}
	conn, _, err := dialer.Dial(wsURL, nil)
	if err != nil {
		fmt.Println("[webrtc-desktop] dial:", err)
		return
	}
	defer conn.Close()

	_ = conn.SetReadDeadline(time.Now().Add(30 * time.Second))
	_, _, _ = conn.ReadMessage()
	_ = conn.SetReadDeadline(time.Time{})

	config := webrtc.Configuration{
		ICEServers: []webrtc.ICEServer{{
			URLs: []string{"stun:stun.l.google.com:19302"},
		}},
	}
	pc, err := webrtc.NewPeerConnection(config)
	if err != nil {
		fmt.Println("[webrtc-desktop] peer:", err)
		_ = writeJSON(conn, map[string]any{"type": "error", "session_id": sessionID, "message": err.Error()})
		return
	}
	defer pc.Close()

	videoTrack, err := webrtc.NewTrackLocalStaticSample(
		webrtc.RTPCodecCapability{MimeType: webrtc.MimeTypeVP8},
		"video", "bhudi-screen",
	)
	if err != nil {
		fmt.Println("[webrtc-desktop] track:", err)
		return
	}
	if _, err := pc.AddTrack(videoTrack); err != nil {
		fmt.Println("[webrtc-desktop] add track:", err)
		return
	}

	pc.OnICECandidate(func(c *webrtc.ICECandidate) {
		if c == nil {
			return
		}
		cand := c.ToJSON()
		_ = writeJSON(conn, map[string]any{
			"type":          "webrtc_ice",
			"session_id":    sessionID,
			"candidate":     cand.Candidate,
			"sdpMid":        cand.SDPMid,
			"sdpMLineIndex": cand.SDPMLineIndex,
		})
	})

	pc.OnConnectionStateChange(func(s webrtc.PeerConnectionState) {
		fmt.Println("[webrtc-desktop] connection state:", s.String())
	})

	offer, err := pc.CreateOffer(nil)
	if err != nil {
		fmt.Println("[webrtc-desktop] offer:", err)
		return
	}
	if err := pc.SetLocalDescription(offer); err != nil {
		fmt.Println("[webrtc-desktop] set local:", err)
		return
	}

	_ = writeJSON(conn, map[string]any{
		"type":       "webrtc_offer",
		"session_id": sessionID,
		"sdp":        offer.SDP,
		"sdpType":    offer.Type.String(),
	})
	_ = writeJSON(conn, map[string]any{
		"type":       "desktop_ready",
		"session_id": sessionID,
		"transport":  "webrtc",
		"encoding":   "vp8",
	})

	for {
		_, raw, err := conn.ReadMessage()
		if err != nil {
			fmt.Println("[webrtc-desktop] read:", err)
			return
		}
		var message map[string]any
		if json.Unmarshal(raw, &message) != nil {
			continue
		}
		msgType := strVal(message["type"])
		inner := message
		if msgType == "dashboard_message" {
			if p, ok := message["payload"].(map[string]any); ok {
				inner = p
				msgType = strVal(p["type"])
			}
		}
		switch msgType {
		case "webrtc_answer":
			sdp := strVal(inner["sdp"])
			if sdp == "" {
				continue
			}
			answer := webrtc.SessionDescription{
				Type: webrtc.SDPTypeAnswer,
				SDP:  sdp,
			}
			if err := pc.SetRemoteDescription(answer); err != nil {
				fmt.Println("[webrtc-desktop] set remote:", err)
			} else {
				fmt.Println("[webrtc-desktop] answer applied")
			}
		case "webrtc_ice":
			cand := strVal(inner["candidate"])
			if cand == "" {
				continue
			}
			ice := webrtc.ICECandidateInit{Candidate: cand}
			if mid := strVal(inner["sdpMid"]); mid != "" {
				ice.SDPMid = &mid
			}
			if err := pc.AddICECandidate(ice); err != nil {
				fmt.Println("[webrtc-desktop] ice:", err)
			}
		case "close":
			fmt.Println("[webrtc-desktop] closed by operator")
			return
		}
	}
}
