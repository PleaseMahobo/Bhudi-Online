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

	procGetDC              = user32.NewProc("GetDC")
	procReleaseDC          = user32.NewProc("ReleaseDC")
	procGetDesktopWindow   = user32.NewProc("GetDesktopWindow")
	procGetSystemMetrics   = user32.NewProc("GetSystemMetrics")
	procSetCursorPos       = user32.NewProc("SetCursorPos")
	procMouseEvent         = user32.NewProc("mouse_event")
	procKeybdEvent         = user32.NewProc("keybd_event")
	procCreateCompatibleDC = gdi32.NewProc("CreateCompatibleDC")
	procCreateDIBSection   = gdi32.NewProc("CreateDIBSection")
	procSelectObject       = gdi32.NewProc("SelectObject")
	procBitBlt             = gdi32.NewProc("BitBlt")
	procDeleteObject       = gdi32.NewProc("DeleteObject")
	procDeleteDC           = gdi32.NewProc("DeleteDC")
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

func primaryDisplayBounds() (image.Rectangle, error) {
	vw, _, _ := procGetSystemMetrics.Call(smCXVirtualScreen)
	vh, _, _ := procGetSystemMetrics.Call(smCYVirtualScreen)
	if vw > 0 && vh > 0 {
		return image.Rect(0, 0, int(vw), int(vh)), nil
	}
	w, _, _ := procGetSystemMetrics.Call(smCXScreen)
	h, _, _ := procGetSystemMetrics.Call(smCYScreen)
	if w == 0 || h == 0 {
		return image.Rectangle{}, fmt.Errorf("GetSystemMetrics returned 0")
	}
	return image.Rect(0, 0, int(w), int(h)), nil
}

func captureOrigin() (int, int) {
	x, _, _ := procGetSystemMetrics.Call(smXVScreen)
	y, _, _ := procGetSystemMetrics.Call(smYVScreen)
	return int(int32(x)), int(int32(y))
}

func capturePrimaryScreen() (image.Image, error) {
	bounds, err := primaryDisplayBounds()
	if err != nil {
		return nil, err
	}
	w, h := bounds.Dx(), bounds.Dy()
	if w <= 0 || h <= 0 {
		return nil, fmt.Errorf("invalid screen size %dx%d", w, h)
	}
	ox, oy := captureOrigin()

	desktop, _, _ := procGetDesktopWindow.Call()
	hdcScreen, _, _ := procGetDC.Call(desktop)
	if hdcScreen == 0 {
		hdcScreen, _, _ = procGetDC.Call(0)
	}
	if hdcScreen == 0 {
		return nil, fmt.Errorf("GetDC failed (run agent in an interactive desktop session, not Session 0)")
	}
	defer procReleaseDC.Call(desktop, hdcScreen)

	hdcMem, _, _ := procCreateCompatibleDC.Call(hdcScreen)
	if hdcMem == 0 {
		return nil, fmt.Errorf("CreateCompatibleDC failed")
	}
	defer procDeleteDC.Call(hdcMem)

	bi := bitmapInfo{
		Header: bitmapInfoHeader{
			Size:        uint32(unsafe.Sizeof(bitmapInfoHeader{})),
			Width:       int32(w),
			Height:      -int32(h),
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

	rop := uintptr(srcCopy | captureBlt)
	ret, _, errBlt := procBitBlt.Call(
		hdcMem, 0, 0, uintptr(w), uintptr(h),
		hdcScreen, uintptr(int32(ox)), uintptr(int32(oy)), rop,
	)
	if ret == 0 {
		ret, _, errBlt = procBitBlt.Call(
			hdcMem, 0, 0, uintptr(w), uintptr(h),
			hdcScreen, uintptr(int32(ox)), uintptr(int32(oy)), srcCopy,
		)
		if ret == 0 {
			return nil, fmt.Errorf("BitBlt failed: %v", errBlt)
		}
	}

	byteCount := w * h * 4
	src := unsafe.Slice((*byte)(bits), byteCount)
	img := image.NewRGBA(image.Rect(0, 0, w, h))
	for i := 0; i < byteCount; i += 4 {
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
	return img, nil
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
