'use client';

import { useState } from 'react';
import { Bot, X, Send, Sparkles } from 'lucide-react';

const EXAMPLE_PROMPTS = [
  'Why is DC01 showing high CPU?',
  'Show machines missing KB506324.',
  'Restart Print Spooler on Finance PCs.',
  'Generate monthly compliance report.',
  'Which users failed MFA today?',
];

type Message = { role: 'user' | 'assistant'; content: string };

export default function AIAssistant() {
  const [open, setOpen] = useState(true);
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);

  const handleSend = () => {
    const text = message.trim();
    if (!text) return;

    setMessages((prev) => [...prev, { role: 'user', content: text }]);
    setMessage('');

    // Placeholder — wire to your real AI / backend endpoint later
    window.setTimeout(() => {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content:
            "I'm analyzing that for you… Connect this panel to your Bhudi AI backend when ready.",
        },
      ]);
    }, 500);
  };

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="fixed bottom-6 right-6 z-50 flex items-center gap-2 px-4 py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-full shadow-lg transition-all"
      >
        <Sparkles className="w-5 h-5" />
        <span className="font-medium text-sm">Ask Bhudi AI</span>
      </button>
    );
  }

  return (
    <aside className="w-80 xl:w-96 h-screen bg-white border-l border-slate-200 flex flex-col shrink-0 sticky top-0">
      {/* Header */}
      <div className="h-14 flex items-center justify-between px-4 border-b border-slate-200 shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center">
            <Bot className="w-4 h-4 text-white" />
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-900">Bhudi AI</p>
            <p className="text-[11px] text-slate-500">Always here to help</p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-500"
          aria-label="Close AI assistant"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 ? (
          <div className="space-y-2">
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">
              Try asking
            </p>
            {EXAMPLE_PROMPTS.map((prompt) => (
              <button
                key={prompt}
                type="button"
                onClick={() => setMessage(prompt)}
                className="w-full text-left text-sm px-3 py-2.5 rounded-lg bg-slate-50 hover:bg-indigo-50 hover:text-indigo-700 text-slate-700 transition-colors border border-slate-100"
              >
                {prompt}
              </button>
            ))}
          </div>
        ) : (
          messages.map((msg, i) => (
            <div
              key={i}
              className={
                msg.role === 'user'
                  ? 'ml-auto max-w-[85%] rounded-2xl rounded-br-md px-3.5 py-2.5 text-sm bg-indigo-600 text-white'
                  : 'max-w-[85%] rounded-2xl rounded-bl-md px-3.5 py-2.5 text-sm bg-slate-100 text-slate-800'
              }
            >
              {msg.content}
            </div>
          ))
        )}
      </div>

      {/* Input */}
      <div className="p-3 border-t border-slate-200 shrink-0">
        <div className="flex gap-2">
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Ask Bhudi AI..."
            className="flex-1 px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
          <button
            type="button"
            onClick={handleSend}
            className="p-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl transition-colors shrink-0"
            aria-label="Send"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
      </div>
    </aside>
  );
}
