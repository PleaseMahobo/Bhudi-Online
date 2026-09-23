package main

import (
	"testing"
)

func TestNumVal(t *testing.T) {
	tests := []struct {
		name     string
		input    any
		expected float64
	}{
		{"float64", float64(42.5), 42.5},
		{"float32", float32(10.5), 10.5},
		{"int", int(100), 100.0},
		{"int64", int64(200), 200.0},
		{"string nil", "not a number", 0.0},
		{"nil", nil, 0.0},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := numVal(tt.input); got != tt.expected {
				t.Errorf("numVal(%v) = %v, want %v", tt.input, got, tt.expected)
			}
		})
	}
}
