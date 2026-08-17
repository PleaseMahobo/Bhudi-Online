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
    case jsonNumber:
        return n.Float64()
    default:
        var f float64
        _, _ = fmt.Sscanf(fmt.Sprint(v), "%f", &f)
        return f
    }
}

type jsonNumber string
func (n jsonNumber) Float64() float64 { var f float64; _, _ = fmt.Sscanf(string(n), "%f", &f); return f }
