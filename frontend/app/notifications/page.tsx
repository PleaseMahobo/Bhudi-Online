'use client';

import React, { useCallback, useEffect, useState } from 'react';
import ModuleShell, { Btn, DataTable, Err, Panel } from '@/shared/components/ModuleShell';
import {
  createNotificationChannel,
  listNotificationCatalog,
  listNotificationChannels,
  listNotificationDeliveries,
  listNotificationTemplates,
  sendNotification,
} from '@/lib/api-modules';

export default function NotificationsPage() {
  const [catalog, setCatalog] = useState<any[]>([]);
  const [channels, setChannels] = useState<any[]>([]);
  const [templates, setTemplates] = useState<any[]>([]);
  const [deliveries, setDeliveries] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [channelId, setChannelId] = useState('');
  const [recipient, setRecipient] = useState('');
  const [body, setBody] = useState('Test notification from Bhudi');

  const load = useCallback(async () => {
    setError(null);
    try {
      const [cat, ch, tpl, del] = await Promise.all([
        listNotificationCatalog(),
        listNotificationChannels(),
        listNotificationTemplates(),
        listNotificationDeliveries({ limit: 40 }),
      ]);
      setCatalog(cat);
      setChannels(ch);
      setTemplates(tpl);
      setDeliveries(del);
      if (!channelId && ch[0]?.id) setChannelId(ch[0].id);
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  }, [channelId]);

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const addSlackChannel = async () => {
    try {
      await createNotificationChannel({
        channel_type: 'slack',
        name: 'Slack (dry-run)',
        enabled: true,
        config: { dry_run: true },
      });
      await load();
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  };

  const onSend = async () => {
    if (!channelId || !recipient) return;
    try {
      await sendNotification({
        channel_id: channelId,
        recipient,
        subject: 'Bhudi notification',
        body,
      });
      await load();
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  };

  return (
    <ModuleShell title="Notification Engine" subtitle="Email, SMS, Teams, Slack, Discord, WhatsApp, Push, Webhooks">
      <Err error={error} />
      <Panel
        title="Channels"
        actions={
          <div className="flex gap-2">
            <Btn variant="ghost" onClick={addSlackChannel}>
              Add dry-run Slack
            </Btn>
            <Btn variant="ghost" onClick={load}>
              Refresh
            </Btn>
          </div>
        }
      >
        <DataTable
          columns={["Name", "Type", "Enabled"]}
          rows={channels.map((c) => [c.name, c.channel_type, String(c.enabled)])}
        />
      </Panel>

      <Panel title="Send test">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
          <select
            className="bg-zinc-950 border border-zinc-700 rounded-xl px-3 py-2 text-sm"
            value={channelId}
            onChange={(e) => setChannelId(e.target.value)}
          >
            <option value="">Select channel</option>
            {channels.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name} ({c.channel_type})
              </option>
            ))}
          </select>
          <input
            className="bg-zinc-950 border border-zinc-700 rounded-xl px-3 py-2 text-sm"
            placeholder="Recipient"
            value={recipient}
            onChange={(e) => setRecipient(e.target.value)}
          />
          <Btn onClick={onSend}>Send</Btn>
        </div>
        <textarea
          className="w-full bg-zinc-950 border border-zinc-700 rounded-xl px-3 py-2 text-sm min-h-[80px]"
          value={body}
          onChange={(e) => setBody(e.target.value)}
        />
      </Panel>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Panel title="Catalog">
          <DataTable
            columns={["Type", "Display"]}
            rows={catalog.map((c) => [c.channel_type, c.display_name])}
          />
        </Panel>
        <Panel title="Templates">
          <DataTable
            columns={["Code", "Name"]}
            rows={templates.map((t) => [t.code, t.name])}
          />
        </Panel>
      </div>

      <Panel title="Recent deliveries">
        <DataTable
          columns={["Recipient", "Status", "Channel", "Created"]}
          rows={deliveries.map((d) => [d.recipient, d.status, d.channel_id, d.created_at])}
        />
      </Panel>
    </ModuleShell>
  );
}
