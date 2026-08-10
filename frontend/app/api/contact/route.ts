import { NextRequest, NextResponse } from 'next/server';
import { appendFile, mkdir } from 'fs/promises';
import path from 'path';

export const runtime = 'nodejs';

type ContactBody = {
  name?: string;
  email?: string;
  company?: string;
  message?: string;
  source?: string;
};

function isEmail(v: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v);
}

async function persistLocal(payload: Record<string, unknown>) {
  const dir = path.join(process.cwd(), '.data');
  try {
    await mkdir(dir, { recursive: true });
    const line = JSON.stringify({ ...payload, received_at: new Date().toISOString() }) + '\n';
    await appendFile(path.join(dir, 'contact-submissions.jsonl'), line, 'utf8');
  } catch {
    // ephemeral hosts may not allow writes — ignore
  }
}

async function postWebhook(payload: Record<string, unknown>) {
  const url = process.env.CONTACT_WEBHOOK_URL || process.env.CRM_WEBHOOK_URL;
  if (!url) return { ok: false as const, skipped: true as const };
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(process.env.CONTACT_WEBHOOK_TOKEN
        ? { Authorization: `Bearer ${process.env.CONTACT_WEBHOOK_TOKEN}` }
        : {}),
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`Webhook ${res.status}: ${text.slice(0, 200)}`);
  }
  return { ok: true as const, skipped: false as const };
}

async function sendResend(payload: {
  name: string;
  email: string;
  company: string;
  message: string;
}) {
  const key = process.env.RESEND_API_KEY;
  if (!key) return { ok: false as const, skipped: true as const };
  const to = process.env.CONTACT_TO_EMAIL || 'hello@bhudi.io';
  const from = process.env.CONTACT_FROM_EMAIL || 'Bhudi <onboarding@resend.dev>';
  const res = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${key}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      from,
      to: [to],
      reply_to: payload.email,
      subject: `Bhudi contact: ${payload.name}${payload.company ? ` (${payload.company})` : ''}`,
      text: [
        `Name: ${payload.name}`,
        `Email: ${payload.email}`,
        `Company: ${payload.company || '—'}`,
        '',
        payload.message,
      ].join('\n'),
    }),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`Resend ${res.status}: ${text.slice(0, 200)}`);
  }
  return { ok: true as const, skipped: false as const };
}

export async function POST(req: NextRequest) {
  let body: ContactBody;
  try {
    body = (await req.json()) as ContactBody;
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  const name = String(body.name || '').trim();
  const email = String(body.email || '').trim().toLowerCase();
  const company = String(body.company || '').trim();
  const message = String(body.message || '').trim();
  const source = String(body.source || 'website-contact').trim();

  if (!name || name.length > 120) {
    return NextResponse.json({ error: 'Name is required' }, { status: 400 });
  }
  if (!email || !isEmail(email) || email.length > 200) {
    return NextResponse.json({ error: 'Valid email is required' }, { status: 400 });
  }
  if (!message || message.length < 10 || message.length > 5000) {
    return NextResponse.json(
      { error: 'Message must be between 10 and 5000 characters' },
      { status: 400 }
    );
  }

  const payload = {
    name,
    email,
    company,
    message,
    source,
    user_agent: req.headers.get('user-agent') || '',
    ip: req.headers.get('x-forwarded-for') || req.headers.get('x-real-ip') || '',
  };

  await persistLocal(payload);

  const channels: string[] = ['local'];
  const errors: string[] = [];

  try {
    const w = await postWebhook(payload);
    if (w.ok) channels.push('webhook');
  } catch (e) {
    errors.push(e instanceof Error ? e.message : 'webhook failed');
  }

  try {
    const r = await sendResend({ name, email, company, message });
    if (r.ok) channels.push('email');
  } catch (e) {
    errors.push(e instanceof Error ? e.message : 'email failed');
  }

  const remoteConfigured = !!(
    process.env.CONTACT_WEBHOOK_URL ||
    process.env.CRM_WEBHOOK_URL ||
    process.env.RESEND_API_KEY
  );
  if (remoteConfigured && channels.length === 1 && errors.length) {
    console.error('[contact]', errors);
    return NextResponse.json(
      {
        ok: true,
        stored: true,
        delivered: false,
        channels,
        warning: 'Saved, but email/CRM delivery failed. Check server logs.',
      },
      { status: 202 }
    );
  }

  return NextResponse.json({
    ok: true,
    stored: true,
    delivered: channels.length > 1,
    channels,
  });
}
