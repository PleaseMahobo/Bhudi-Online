//go:build windows

package main

import (
	"reflect"
	"testing"
)

func TestFirstString(t *testing.T) {
	tests := []struct {
		name     string
		payload  map[string]any
		keys     []string
		expected string
	}{
		{
			name:     "empty payload",
			payload:  map[string]any{},
			keys:     []string{"kb", "kb_article"},
			expected: "",
		},
		{
			name: "first key present",
			payload: map[string]any{
				"kb": "KB5001234",
			},
			keys:     []string{"kb", "kb_article"},
			expected: "KB5001234",
		},
		{
			name: "fallback to second key",
			payload: map[string]any{
				"kb_article": "KB5005678",
			},
			keys:     []string{"kb", "kb_article", "update_id"},
			expected: "KB5005678",
		},
		{
			name: "ignores empty strings and whitespace",
			payload: map[string]any{
				"kb":         "   ",
				"kb_article": "KB5009999",
			},
			keys:     []string{"kb", "kb_article"},
			expected: "KB5009999",
		},
		{
			name: "ignores non-string types",
			payload: map[string]any{
				"kb":         12345,
				"kb_article": "KB5009999",
			},
			keys:     []string{"kb", "kb_article"},
			expected: "KB5009999",
		},
		{
			name: "trims result whitespace",
			payload: map[string]any{
				"update_id": "  abc-123-def  ",
			},
			keys:     []string{"kb", "kb_article", "update_id"},
			expected: "abc-123-def",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			actual := firstString(tt.payload, tt.keys...)
			if actual != tt.expected {
				t.Errorf("firstString() = %q, want %q", actual, tt.expected)
			}
		})
	}
}

func TestFirstNonEmpty(t *testing.T) {
	if got := firstNonEmpty("hello", "world"); got != "hello" {
		t.Errorf("firstNonEmpty('hello', 'world') = %q, want 'hello'", got)
	}
	if got := firstNonEmpty("", "world"); got != "world" {
		t.Errorf("firstNonEmpty('', 'world') = %q, want 'world'", got)
	}
	if got := firstNonEmpty("   ", "world"); got != "world" {
		t.Errorf("firstNonEmpty('   ', 'world') = %q, want 'world'", got)
	}
}

func TestTryParseJSON(t *testing.T) {
	if got := tryParseJSON(""); got != nil {
		t.Errorf("tryParseJSON('') = %v, want nil", got)
	}
	if got := tryParseJSON("invalid json"); got != nil {
		t.Errorf("tryParseJSON('invalid json') = %v, want nil", got)
	}
	valid := `{"platform":"windows","count":0}`
	got := tryParseJSON(valid)
	if got == nil {
		t.Fatalf("tryParseJSON(%q) = nil, want map", valid)
	}
	m, ok := got.(map[string]any)
	if !ok {
		t.Fatalf("tryParseJSON(%q) type = %T, want map[string]any", valid, got)
	}
	if !reflect.DeepEqual(m["platform"], "windows") {
		t.Errorf("platform = %v, want 'windows'", m["platform"])
	}
}
