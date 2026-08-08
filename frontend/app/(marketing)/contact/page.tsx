'use client';

import { useState } from 'react';

export default function ContactPage() {
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    // Front-end placeholder — wire to API / email later
    setTimeout(() => {
      setLoading(false);
      setSent(true);
    }, 600);
  };

  return (
    <div className="mx-auto max-w-xl px-4 py-16 sm:px-6">
      <p className="text-sm font-semibold text-indigo-600">Contact</p>
      <h1 className="mt-2 text-4xl font-bold tracking-tight text-[#0F172A]">
        Book a demo or ask a question
      </h1>
      <p className="mt-4 text-slate-600">
        Tell us about your environment. We&apos;ll follow up with a tailored walkthrough.
      </p>

      {sent ? (
        <div className="mt-10 rounded-2xl border border-emerald-200 bg-emerald-50 p-6 text-emerald-900">
          <p className="font-semibold">Message received</p>
          <p className="mt-1 text-sm text-emerald-800">
            Thanks — our team will get back to you shortly.
          </p>
        </div>
      ) : (
        <form onSubmit={onSubmit} className="mt-10 space-y-4">
          <div>
            <label className="text-xs font-medium text-slate-600">Name</label>
            <input
              required
              name="name"
              className="mt-1 w-full rounded-xl border border-slate-300 px-4 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
            />
          </div>
          <div>
            <label className="text-xs font-medium text-slate-600">Work email</label>
            <input
              required
              type="email"
              name="email"
              className="mt-1 w-full rounded-xl border border-slate-300 px-4 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
            />
          </div>
          <div>
            <label className="text-xs font-medium text-slate-600">Company</label>
            <input
              name="company"
              className="mt-1 w-full rounded-xl border border-slate-300 px-4 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
            />
          </div>
          <div>
            <label className="text-xs font-medium text-slate-600">Message</label>
            <textarea
              required
              name="message"
              rows={5}
              className="mt-1 w-full rounded-xl border border-slate-300 px-4 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
              placeholder="MSP or enterprise? Approx. endpoints? What matters most?"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-60"
          >
            {loading ? 'Sending…' : 'Send message'}
          </button>
        </form>
      )}
    </div>
  );
}
