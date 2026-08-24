'use client';

import { useEffect, useRef, useState } from 'react';
import { Bot, X, Send, Sparkles, Loader2 } from 'lucide-react';

const EXAMPLE_PROMPTS = [
  'Why is DC01 showing high CPU?',
  'Show machines missing critical patches.',
  'Restart Print Spooler on Finance PCs.',
  'Generate monthly compliance report.',
  'Which users failed MFA today?',
];

type Message = { role: 'user' | 'assistant'; content: string };

async function askBhudiAi(
  message: string,
  history: Message[]
): Promise<{ reply: string; mode?: string; suggestions?: string[] }> {
  const res = await fetch('/api/v1/ai/chat', {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({
      message,
      history: history.slice(-8).map((m) => ({ role: m.role, content: m.content })),
    }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail =
      typeof data?.detail === 'string'
        ? data.detail
        : data?.message || `AI request failed (${res.status})`;
    throw new Error(detail);
  }
  return data;
}

export default function AIAssistant() {
  const [open, setOpen] = useState(true);
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content:
        'Hi — I am Bhudi AI. Ask about devices, patches, print, alerts, or MFA. I use live models when configured, otherwise guided playbooks.',
    },
  ]);
  const [loading, setLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>(EXAMPLE_PROMPTS);
  const [mode, setMode] = useState<string>('');
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }, [messages, loading]);

  async function handleSend(textOverride?: string) {
    const text = (textOverride ?? message).trim();
    if (!text || loading) return;

    setMessages((prev) => [...prev, { role: 'user', content: text }]);
    setMessage('');
    setLoading(true);

    try {
      const result = await askBhudiAi(text, messages);
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: result.reply || 'No response generated.' },
      ]);
      if (result.mode) setMode(result.mode);
      if (Array.isArray(result.suggestions) && result.suggestions.length) {
        setSuggestions(result.suggestions);
      }
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content:
            err?.message ||
            'Could not reach the AI service. Check API deploy and that /api/v1/ai/chat is routed.',
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="m-3 shrink-0 self-end rounded-full bg-indigo-600 px-3 py-2 text-white shadow-md hover:bg-indigo-700"
      >
        <span className="inline-flex items-center gap-2 text-sm font-medium">
          <Sparkles className="h-4 w-4" /> Ask Bhudi AI
        </span>
      </button>
    );
  }

  return (
    <aside className="flex h-full w-72 shrink-0 flex-col border-l border-slate-200 bg-white xl:w-80">
      <div className="flex h-12 shrink-0 items-center justify-between border-b border-slate-200 px-3">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-600">
            <Bot className="h-4 w-4 text-white" />
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-900">Bhudi AI</p>
            <p className="text-[10px] text-slate-500">
              {mode === 'live'
                ? 'Live model'
                : mode === 'heuristic'
                  ? 'Guided mode'
                  : 'Always here to help'}
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100"
          aria-label="Close AI assistant"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="min-h-0 flex-1 space-y-2 overflow-y-auto p-3">
        {messages.map((m, i) => (
          <div
            key={`${m.role}-${i}`}
            className={`whitespace-pre-wrap rounded-xl px-3 py-2 text-xs leading-relaxed ${
              m.role === 'user'
                ? 'ml-4 bg-indigo-600 text-white'
                : 'mr-3 border border-slate-200 bg-slate-50 text-slate-800'
            }`}
          >
            {m.content}
          </div>
        ))}
        {loading && (
          <div className="mr-3 flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-500">
            <Loader2 className="h-3.5 w-3.5 animate-spin" /> Thinking…
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="shrink-0 border-t border-slate-200 p-2.5">
        <div className="mb-1.5 flex flex-wrap gap-1">
          {suggestions.slice(0, 2).map((s) => (
            <button
              key={s}
              type="button"
              disabled={loading}
              onClick={() => void handleSend(s)}
              className="rounded-full border border-slate-200 bg-white px-2 py-1 text-[10px] text-slate-600 hover:border-indigo-300 hover:text-indigo-700 disabled:opacity-50"
            >
              {s}
            </button>
          ))}
        </div>
        <form
          className="flex items-end gap-1.5"
          onSubmit={(e) => {
            e.preventDefault();
            void handleSend();
          }}
        >
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                void handleSend();
              }
            }}
            rows={2}
            placeholder="Ask Bhudi AI…"
            className="min-w-0 flex-1 resize-none rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-2 text-xs text-slate-900 outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/20"
          />
          <button
            type="submit"
            disabled={loading || !message.trim()}
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50"
            aria-label="Send"
          >
            {loading ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Send className="h-3.5 w-3.5" />
            )}
          </button>
        </form>
      </div>
    </aside>
  );
}
