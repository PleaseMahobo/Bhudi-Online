//go:build !windows

package main

import "fmt"

func numVal(v any) float64 {
    switch n := v.(type) {
    case float64:
        return n
    case float32:
        return float64(n)
    case int:
        return float64(n)
    case int64:
        return float64(n)
    default:
        var f float64
        _, _ = fmt.Sscanf(fmt.Sprint(v), "%f", &f)
        return f
    }
}
