//go:build release

package main

import _ "embed"

//go:embed bhudi-support.exe
var bundledSupportClient []byte
