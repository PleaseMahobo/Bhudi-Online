//go:build windows

package main

import (
	"fmt"
	"image"
	"strings"
	"syscall"
	"unsafe"
)

var (
	user32 = syscall.NewLazyDLL("user32.dll")
	gdi32  = syscall.NewLazyDLL("gdi32.dll")

	procGetDC                = user32.NewProc("GetDC")
	procReleaseDC            = user32.NewProc("ReleaseDC")
	procGetDesktopWindow     = user32.NewProc("GetDesktopWindow")
	procGetSystemMetrics     = user32.NewProc("GetSystemMetrics")
	procSetCursorPos         = user32.NewProc("SetCursorPos")
	procMouseEvent           = user32.NewProc("mouse_event")
	procKeybdEvent           = user32.NewProc("keybd_event")
	procEnumDisplayMonitors  = user32.NewProc("EnumDisplayMonitors")
	procGetMonitorInfoW      = user32.NewProc("GetMonitorInfoW")
	procCreateCompatibleDC   = gdi32.NewProc("CreateCompatibleDC")
	procCreateCompatibleBitmap = gdi32.NewProc("CreateCompatibleBitmap")
	procCreateDIBSection     = gdi32.NewProc("CreateDIBSection")
	procSelectObject         = gdi32.NewProc("SelectObject")
	procBitBlt               = gdi32.NewProc("BitBlt")
	procDeleteObject         = gdi32.NewProc("DeleteObject")
	procDeleteDC             = gdi32.NewProc("DeleteDC")
	procGetDIBits            = gdi32.NewProc("GetDIBits")
)

const (
	smCXScreen        = 0
	smCYScreen        = 1
	smCXVirtualScreen = 78
	smCYVirtualScreen = 79
	smXVScreen        = 76
	smYVScreen        = 77

	srcCopy    = 0x00CC0020
	captureBlt = 0x40000000
	biRGB      = 0
	dibRGBColors = 0

	mouseEventFLeftDown   = 0x0002
	mouseEventFLeftUp     = 0x0004
	mouseEventFRightDown  = 0x0008
	mouseEventFRightUp    = 0x0010
	mouseEventFMiddleDown = 0x0020
	mouseEventFMiddleUp   = 0x0040
	mouseEventFWheel      = 0x0800

	keyeventfKeyup = 0x0002
)

type bitmapInfoHeader struct {
	Size          uint32
	Width         int32
	Height        int32
	Planes        uint16
	BitCount      uint16
	Compression   uint32
	SizeImage     uint32
	XPelsPerMeter int32
	YPelsPerMeter int32
	ClrUsed       uint32
	ClrImportant  uint32
}

type bitmapInfo struct {
	Header bitmapInfoHeader
}

type rectWin struct {
	Left, Top, Right, Bottom int32
}

type monitorInfo struct {
	Size    uint32
	Monitor rectWin
	Work    rectWin
	Flags   uint32
}

func primaryDisplayBounds() (image.Rectangle, error) {
	x, y, w, h, err := monitorRect(0)
	if err != nil {
		return image.Rectangle{}, err
	}
	return image.Rect(x, y, x+w, y+h), nil
}

func captureOrigin() (int, int) {
	x, _, _ := procGetSystemMetrics.Call(smXVScreen)
	y, _, _ := procGetSystemMetrics.Call(smYVScreen)
	return int(int32(x)), int(int32(y))
}

func listMonitors() []MonitorInfo {
	var out []MonitorInfo
	cb := syscall.NewCallback(func(hMonitor, hdcMonitor, lprc uintptr, dwData uintptr) uintptr {
		var mi monitorInfo
		mi.Size = uint32(unsafe.Sizeof(mi))
		r, _, _ := procGetMonitorInfoW.Call(hMonitor, uintptr(unsafe.Pointer(&mi)))
		if r == 0 {
			return 1
		}
		w := int(mi.Monitor.Right - mi.Monitor.Left)
		h := int(mi.Monitor.Bottom - mi.Monitor.Top)
		if w <= 0 || h <= 0 {
			return 1
		}
		out = append(out, MonitorInfo{
			Index:   len(out),
			Name:    fmt.Sprintf("Display %d", len(out)+1),
			X:       int(mi.Monitor.Left),
			Y:       int(mi.Monitor.Top),
			Width:   w,
			Height:  h,
			Primary: mi.Flags&1 != 0,
		})
		return 1
	})
	procEnumDisplayMonitors.Call(0, 0, cb, 0)
	if len(out) == 0 {
		w, _, _ := procGetSystemMetrics.Call(smCXScreen)
		h, _, _ := procGetSystemMetrics.Call(smCYScreen)
		if w > 0 && h > 0 {
			out = []MonitorInfo{{
				Index: 0, Name: "Primary", Width: int(w), Height: int(h), Primary: true,
			}}
		}
	}
	return out
}

func monitorRect(index int) (x, y, w, h int, err error) {
	mons := listMonitors()
	if len(mons) == 0 {
		return 0, 0, 0, 0, fmt.Errorf("no monitors detected")
	}
	if index < 0 || index >= len(mons) {
		index = 0
		for i, m := range mons {
			if m.Primary {
				index = i
				break
			}
		}
	}
	m := mons[index]
	return m.X, m.Y, m.Width, m.Height, nil
}

// captureScreenRegion captures one monitor (or primary if index is out of range).
func captureScreenRegion(monitorIndex int) (image.Image, error) {
	x, y, w, h, err := monitorRect(monitorIndex)
	if err != nil {
		return nil, err
	}
	return captureRect(x, y, w, h)
}

func capturePrimaryScreen() (image.Image, error) {
	return captureScreenRegion(0)
}

// captureRect grabs a screen rectangle using CreateDIBSection (preferred) or
// CreateCompatibleBitmap + GetDIBits (fallback). Avoids the common GetDIBits
// failures from mismatched biHeight/stride when used alone.
func captureRect(srcX, srcY, w, h int) (image.Image, error) {
	if w <= 0 || h <= 0 {
		return nil, fmt.Errorf("invalid capture size %dx%d", w, h)
	}

	desktop, _, _ := procGetDesktopWindow.Call()
	hdcScreen, _, _ := procGetDC.Call(desktop)
	if hdcScreen == 0 {
		hdcScreen, _, _ = procGetDC.Call(0)
	}
	if hdcScreen == 0 {
		return nil, fmt.Errorf("GetDC failed — agent must run in an interactive user desktop (not Session 0 / pure service)")
	}
	defer procReleaseDC.Call(desktop, hdcScreen)

	hdcMem, _, _ := procCreateCompatibleDC.Call(hdcScreen)
	if hdcMem == 0 {
		return nil, fmt.Errorf("CreateCompatibleDC failed")
	}
	defer procDeleteDC.Call(hdcMem)

	// Preferred path: top-down 32-bpp DIB section (bits pointer, no GetDIBits).
	img, err := captureViaDIBSection(hdcScreen, hdcMem, srcX, srcY, w, h)
	if err == nil {
		return img, nil
	}

	// Fallback: compatible bitmap + GetDIBits with correct bottom-up layout.
	img2, err2 := captureViaGetDIBits(hdcScreen, hdcMem, srcX, srcY, w, h)
	if err2 == nil {
		return img2, nil
	}
	return nil, fmt.Errorf("screen capture failed (DIBSection: %v; GetDIBits: %v)", err, err2)
}

func captureViaDIBSection(hdcScreen, hdcMem uintptr, srcX, srcY, w, h int) (image.Image, error) {
	bi := bitmapInfo{
		Header: bitmapInfoHeader{
			Size:        uint32(unsafe.Sizeof(bitmapInfoHeader{})),
			Width:       int32(w),
			Height:      -int32(h), // top-down
			Planes:      1,
			BitCount:    32,
			Compression: biRGB,
		},
	}
	var bits unsafe.Pointer
	hbm, _, errCall := procCreateDIBSection.Call(
		hdcScreen,
		uintptr(unsafe.Pointer(&bi)),
		dibRGBColors,
		uintptr(unsafe.Pointer(&bits)),
		0,
		0,
	)
	if hbm == 0 || bits == nil {
		return nil, fmt.Errorf("CreateDIBSection failed: %v", errCall)
	}
	defer procDeleteObject.Call(hbm)

	prev, _, _ := procSelectObject.Call(hdcMem, hbm)
	if prev == 0 {
		return nil, fmt.Errorf("SelectObject failed")
	}
	defer procSelectObject.Call(hdcMem, prev)

	if err := bitBltScreen(hdcMem, hdcScreen, srcX, srcY, w, h); err != nil {
		return nil, err
	}

	return bgraToRGBA(unsafe.Slice((*byte)(bits), w*h*4), w, h), nil
}

func captureViaGetDIBits(hdcScreen, hdcMem uintptr, srcX, srcY, w, h int) (image.Image, error) {
	hbm, _, _ := procCreateCompatibleBitmap.Call(hdcScreen, uintptr(w), uintptr(h))
	if hbm == 0 {
		return nil, fmt.Errorf("CreateCompatibleBitmap failed")
	}
	defer procDeleteObject.Call(hbm)

	prev, _, _ := procSelectObject.Call(hdcMem, hbm)
	if prev == 0 {
		return nil, fmt.Errorf("SelectObject failed")
	}
	defer procSelectObject.Call(hdcMem, prev)

	if err := bitBltScreen(hdcMem, hdcScreen, srcX, srcY, w, h); err != nil {
		return nil, err
	}

	// Bottom-up DIB; stride DWORD-aligned for 32-bpp = w*4 already when w is fine,
	// but use explicit SizeImage.
	stride := ((w*32 + 31) / 32) * 4
	buf := make([]byte, stride*h)
	bi := bitmapInfo{
		Header: bitmapInfoHeader{
			Size:        uint32(unsafe.Sizeof(bitmapInfoHeader{})),
			Width:       int32(w),
			Height:      int32(h), // positive = bottom-up for GetDIBits
			Planes:      1,
			BitCount:    32,
			Compression: biRGB,
			SizeImage:   uint32(stride * h),
		},
	}

	// hdc must be the mem DC that currently has the bitmap selected (or 0).
	ret, _, errCall := procGetDIBits.Call(
		hdcMem,
		hbm,
		0,
		uintptr(h),
		uintptr(unsafe.Pointer(&buf[0])),
		uintptr(unsafe.Pointer(&bi)),
		dibRGBColors,
	)
	if ret == 0 {
		return nil, fmt.Errorf("GetDIBits failed: %v", errCall)
	}

	// Flip bottom-up → top-down RGBA
	img := image.NewRGBA(image.Rect(0, 0, w, h))
	for row := 0; row < h; row++ {
		srcRow := buf[(h-1-row)*stride : (h-1-row)*stride+w*4]
		dstRow := img.Pix[row*img.Stride : row*img.Stride+w*4]
		for col := 0; col < w; col++ {
			i := col * 4
			b, g, r := srcRow[i], srcRow[i+1], srcRow[i+2]
			dstRow[i] = r
			dstRow[i+1] = g
			dstRow[i+2] = b
			dstRow[i+3] = 255
		}
	}
	return img, nil
}

func bitBltScreen(hdcMem, hdcScreen uintptr, srcX, srcY, w, h int) error {
	rop := uintptr(srcCopy | captureBlt)
	ret, _, errBlt := procBitBlt.Call(
		hdcMem, 0, 0, uintptr(w), uintptr(h),
		hdcScreen, uintptr(int32(srcX)), uintptr(int32(srcY)), rop,
	)
	if ret == 0 {
		ret, _, errBlt = procBitBlt.Call(
			hdcMem, 0, 0, uintptr(w), uintptr(h),
			hdcScreen, uintptr(int32(srcX)), uintptr(int32(srcY)), srcCopy,
		)
		if ret == 0 {
			return fmt.Errorf("BitBlt failed: %v", errBlt)
		}
	}
	return nil
}

func bgraToRGBA(src []byte, w, h int) *image.RGBA {
	img := image.NewRGBA(image.Rect(0, 0, w, h))
	for i := 0; i+3 < len(src) && i+3 < len(img.Pix); i += 4 {
		b, g, r, a := src[i], src[i+1], src[i+2], src[i+3]
		img.Pix[i] = r
		img.Pix[i+1] = g
		img.Pix[i+2] = b
		if a == 0 {
			img.Pix[i+3] = 255
		} else {
			img.Pix[i+3] = a
		}
	}
	return img
}

func applyDesktopInputAt(ev map[string]any, frameW, frameH, originX, originY int) {
	if frameW <= 0 || frameH <= 0 {
		applyDesktopInput(ev, image.Rect(0, 0, 1920, 1080))
		return
	}
	// Map normalized or frame-space coords onto the captured region origin.
	t := strVal(ev["type"])
	nx := numVal(ev["x"])
	ny := numVal(ev["y"])
	x, y := int(nx), int(ny)
	if nx <= 1.0 && ny <= 1.0 && (nx > 0 || ny > 0 || t == "mousemove" || t == "mouse") {
		x = int(nx * float64(frameW))
		y = int(ny * float64(frameH))
	}
	ev2 := map[string]any{}
	for k, v := range ev {
		ev2[k] = v
	}
	ev2["x"] = float64(x + originX)
	ev2["y"] = float64(y + originY)
	// applyDesktopInput adds captureOrigin again for virtual-screen coords when
	// using absolute pixel values — strip that by using absolute path below.
	applyDesktopInputAbsolute(ev2)
}

func applyDesktopInputAbsolute(ev map[string]any) {
	t := strVal(ev["type"])
	x := int(numVal(ev["x"]))
	y := int(numVal(ev["y"]))
	button := strings.ToLower(strVal(ev["button"]))
	key := strVal(ev["key"])
	if key == "" {
		key = strVal(ev["code"])
	}

	switch t {
	case "mousemove", "mouse":
		procSetCursorPos.Call(uintptr(x), uintptr(y))
	case "mousedown", "click":
		procSetCursorPos.Call(uintptr(x), uintptr(y))
		flag := uintptr(mouseEventFLeftDown)
		if button == "right" {
			flag = mouseEventFRightDown
		} else if button == "middle" {
			flag = mouseEventFMiddleDown
		}
		procMouseEvent.Call(flag, 0, 0, 0, 0)
		if t == "click" {
			up := uintptr(mouseEventFLeftUp)
			if button == "right" {
				up = mouseEventFRightUp
			} else if button == "middle" {
				up = mouseEventFMiddleUp
			}
			procMouseEvent.Call(up, 0, 0, 0, 0)
		}
	case "mouseup":
		procSetCursorPos.Call(uintptr(x), uintptr(y))
		flag := uintptr(mouseEventFLeftUp)
		if button == "right" {
			flag = mouseEventFRightUp
		} else if button == "middle" {
			flag = mouseEventFMiddleUp
		}
		procMouseEvent.Call(flag, 0, 0, 0, 0)
	case "wheel":
		delta := int(numVal(ev["deltaY"]))
		if delta == 0 {
			delta = int(numVal(ev["delta"]))
		}
		if delta == 0 {
			delta = -120
		}
		procMouseEvent.Call(mouseEventFWheel, 0, 0, uintptr(uint32(delta)), 0)
	case "keydown", "keypress", "keyboard":
		vk := virtualKey(key)
		if vk != 0 {
			procKeybdEvent.Call(uintptr(vk), 0, 0, 0)
			if t == "keypress" {
				procKeybdEvent.Call(uintptr(vk), 0, keyeventfKeyup, 0)
			}
		}
	case "keyup":
		vk := virtualKey(key)
		if vk != 0 {
			procKeybdEvent.Call(uintptr(vk), 0, keyeventfKeyup, 0)
		}
	}
}

func applyDesktopInput(ev map[string]any, bounds image.Rectangle) {
	t := strVal(ev["type"])
	x := int(numVal(ev["x"]))
	y := int(numVal(ev["y"]))
	if x <= 1 && y <= 1 && (numVal(ev["x"]) <= 1.0) {
		x = int(numVal(ev["x"]) * float64(bounds.Dx()))
		y = int(numVal(ev["y"]) * float64(bounds.Dy()))
	}
	ox, oy := captureOrigin()
	x += ox
	y += oy
	ev2 := map[string]any{}
	for k, v := range ev {
		ev2[k] = v
	}
	ev2["x"] = float64(x)
	ev2["y"] = float64(y)
	ev2["type"] = t
	applyDesktopInputAbsolute(ev2)
}

func numVal(v any) float64 {
	switch t := v.(type) {
	case float64:
		return t
	case float32:
		return float64(t)
	case int:
		return float64(t)
	case int64:
		return float64(t)
	default:
		return 0
	}
}

func virtualKey(key string) byte {
	if key == "" {
		return 0
	}
	if len(key) == 1 {
		c := key[0]
		if c >= 'a' && c <= 'z' {
			return c - 32
		}
		if (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') {
			return c
		}
	}
	switch strings.ToLower(key) {
	case "enter", "return":
		return 0x0D
	case "escape", "esc":
		return 0x1B
	case "tab":
		return 0x09
	case "backspace":
		return 0x08
	case "space", " ":
		return 0x20
	case "delete", "del":
		return 0x2E
	case "arrowup", "up":
		return 0x26
	case "arrowdown", "down":
		return 0x28
	case "arrowleft", "left":
		return 0x25
	case "arrowright", "right":
		return 0x27
	case "shift":
		return 0x10
	case "control", "ctrl":
		return 0x11
	case "alt":
		return 0x12
	case "win", "meta":
		return 0x5B
	case "f1":
		return 0x70
	case "f2":
		return 0x71
	case "f3":
		return 0x72
	case "f4":
		return 0x73
	case "f5":
		return 0x74
	default:
		return 0
	}
}
