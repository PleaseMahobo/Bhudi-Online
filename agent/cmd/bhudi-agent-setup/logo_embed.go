//go:build windows

package main

// logoPNGBase64 holds the Bhudi RMMS logo as a base64-encoded PNG.
// Populate this constant (or set it in init) before a release build so the
// installer GUI shows the brand mark. Leave empty for a text-only wizard.
//
// Example local generation:
//   base64 -w0 bhudi-logo.png > logo.b64
// then paste into the string below.
func init() {
	// Intentionally empty in source control until brand asset is committed.
	// CI may inject the value via -ldflags or a generated file.
	if logoPNGBase64 == "" {
		logoPNGBase64 = ""
	}
}
