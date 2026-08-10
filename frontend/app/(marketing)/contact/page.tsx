'use client';

import { useState } from 'react';
import { Mail, MessageSquare, Building2, Loader2 } from 'lucide-react';
import { PageHero, SectionLabel } from '@/shared/marketing/MarketingUI';

export default function ContactPage() {
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [warning, setWarning] = useState('');

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError('');
    setWarning('');
    const fd = new FormData(e.currentTarget);
    const body = {
      name: String(fd.get('name') || ''),
      email: String(fd.get('email') || ''),
      company: String(fd.get('company') || ''),
      message: String(fd.get('message') || ''),
      source: 'website-contact',
    };
    try {
      const res = await fetch('/api/contact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.error || res.statusText || 'Failed to send');
      }
      if (data.warning) setWarning(String(data.warning));
      setSent(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send message');
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHero
        label="Contact"
        title="Talk to the Bhudi team"
        subtitle="Sales, demos, partnership, or support — send a note and we will route it to the right person."
      />

      <section className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <div className="grid gap-12 lg:grid-cols-5">
          <div className="space-y-6 lg:col-span-2">
            <SectionLabel>Channels</SectionLabel>
            {[
              { icon: Mail, t: 'Email', d: 'hello@bhudi.io' },
              { icon: MessageSquare, t: 'Demo', d: 'Book a walkthrough of the operations shell' },
              { icon: Building2, t: 'Partners', d: 'MSP and integrator programs' },
            ].map(({ icon: Icon, t, d }) => (
              <div key={t} className="flex gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600">
                  <Icon size={18} />
                </div>
                <div>
                  <p className="font-semibold text-slate-900">{t}</p>
                  <p className="text-sm text-slate-600">{d}</p>
                </div>
              </div>
            ))}
          </div>

          <div className="lg:col-span-3">
            {sent ? (
              <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-8 text-emerald-900">
                <h2 className="text-lg font-semibold">Message received</h2>
                <p className="mt-2 text-sm">
                  Thanks — your message was submitted successfully. We typically respond within one
                  business day.
                </p>
                {warning && <p className="mt-3 text-sm text-amber-800">{warning}</p>}
              </div>
            ) : (
              <form
                onSubmit={onSubmit}
                className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8"
              >
                <div className="grid gap-4 sm:grid-cols-2">
                  <label className="block text-sm">
                    <span className="font-medium text-slate-700">Name</span>
                    <input
                      required
                      name="name"
                      maxLength={120}
                      className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2"
                    />
                  </label>
                  <label className="block text-sm">
                    <span className="font-medium text-slate-700">Work email</span>
                    <input
                      required
                      type="email"
                      name="email"
                      maxLength={200}
                      className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2"
                    />
                  </label>
                </div>
                <label className="mt-4 block text-sm">
                  <span className="font-medium text-slate-700">Company</span>
                  <input
                    name="company"
                    maxLength={200}
                    className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2"
                  />
                </label>
                <label className="mt-4 block text-sm">
                  <span className="font-medium text-slate-700">How can we help?</span>
                  <textarea
                    required
                    name="message"
                    rows={5}
                    minLength={10}
                    maxLength={5000}
                    className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2"
                  />
                </label>
                {error && (
                  <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
                )}
                <button
                  type="submit"
                  disabled={busy}
                  className="mt-6 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-60 sm:w-auto"
                >
                  {busy ? <Loader2 size={16} className="animate-spin" /> : null}
                  Send message
                </button>
              </form>
            )}
          </div>
        </div>
      </section>
    </>
  );
}
