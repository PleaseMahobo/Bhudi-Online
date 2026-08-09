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
	user32   = syscall.NewLazyDLL("user32.dll")
	gdi32    = syscall.NewLazyDLL("gdi32.dll")

	procGetDC                  = user32.NewProc("GetDC")
	procReleaseDC              = user32.NewProc("ReleaseDC")
	procGetSystemMetrics       = user32.NewProc("GetSystemMetrics")
	procSetCursorPos           = user32.NewProc("SetCursorPos")
	procMouseEvent             = user32.NewProc("mouse_event")
	procKeybdEvent             = user32.NewProc("keybd_event")
	procCreateCompatibleDC     = gdi32.NewProc("CreateCompatibleDC")
	procCreateCompatibleBitmap = gdi32.NewProc("CreateCompatibleBitmap")
	procSelectObject           = gdi32.NewProc("SelectObject")
	procBitBlt                 = gdi32.NewProc("BitBlt")
	procDeleteObject           = gdi32.NewProc("DeleteObject")
	procDeleteDC               = gdi32.NewProc("DeleteDC")
	procGetDIBits              = gdi32.NewProc("GetDIBits")
)

const (
	smCXScreen = 0
	smCYScreen = 1
	srcCopy    = 0x00CC0020
	biRGB      = 0
	dibRGBColors = 0

	mouseEventFMove       = 0x0001
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

func primaryDisplayBounds() (image.Rectangle, error) {
	w, _, _ := procGetSystemMetrics.Call(smCXScreen)
	h, _, _ := procGetSystemMetrics.Call(smCYScreen)
	if w == 0 || h == 0 {
		return image.Rectangle{}, fmt.Errorf("GetSystemMetrics returned 0")
	}
	return image.Rect(0, 0, int(w), int(h)), nil
}

func capturePrimaryScreen() (image.Image, error) {
	bounds, err := primaryDisplayBounds()
	if err != nil {
		return nil, err
	}
	w, h := bounds.Dx(), bounds.Dy()

	hdcScreen, _, _ := procGetDC.Call(0)
	if hdcScreen == 0 {
		return nil, fmt.Errorf("GetDC failed")
	}
	defer procReleaseDC.Call(0, hdcScreen)

	hdcMem, _, _ := procCreateCompatibleDC.Call(hdcScreen)
	if hdcMem == 0 {
		return nil, fmt.Errorf("CreateCompatibleDC failed")
	}
	defer procDeleteDC.Call(hdcMem)

	hbm, _, _ := procCreateCompatibleBitmap.Call(hdcScreen, uintptr(w), uintptr(h))
	if hbm == 0 {
		return nil, fmt.Errorf("CreateCompatibleBitmap failed")
	}
	defer procDeleteObject.Call(hbm)

	procSelectObject.Call(hdcMem, hbm)
	ret, _, _ := procBitBlt.Call(hdcMem, 0, 0, uintptr(w), uintptr(h), hdcScreen, 0, 0, srcCopy)
	if ret == 0 {
		return nil, fmt.Errorf("BitBlt failed")
	}

	bi := bitmapInfoHeader{
		Size:        uint32(unsafe.Sizeof(bitmapInfoHeader{})),
		Width:       int32(w),
		Height:      -int32(h),
		Planes:      1,
		BitCount:    32,
		Compression: biRGB,
	}

	buf := make([]byte, w*h*4)
	ret, _, _ = procGetDIBits.Call(
		hdcMem, hbm, 0, uintptr(h),
		uintptr(unsafe.Pointer(&buf[0])),
		uintptr(unsafe.Pointer(&bi)),
		dibRGBColors,
	)
	if ret == 0 {
		return nil, fmt.Errorf("GetDIBits failed")
	}

	img := image.NewRGBA(bounds)
	for i := 0; i < len(buf); i += 4 {
		b, g, r, a := buf[i], buf[i+1], buf[i+2], buf[i+3]
		j := i
		img.Pix[j] = r
		img.Pix[j+1] = g
		img.Pix[j+2] = b
		img.Pix[j+3] = a
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
