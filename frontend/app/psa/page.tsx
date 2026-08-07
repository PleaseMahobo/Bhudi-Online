'use client';

import React, { useCallback, useEffect, useState } from 'react';
import ModuleShell, { Btn, DataTable, Err, Panel } from '@/shared/components/ModuleShell';
import {
  listPsaCatalog,
  listPsaConnections,
  listPsaSyncEvents,
  listPsaTicketLinks,
} from '@/lib/api-modules';

export default function PsaPage() {
  const [catalog, setCatalog] = useState<any[]>([]);
  const [connections, setConnections] = useState<any[]>([]);
  const [events, setEvents] = useState<any[]>([]);
  const [links, setLinks] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [c, conn, ev, lk] = await Promise.all([
        listPsaCatalog(),
        listPsaConnections(),
        listPsaSyncEvents(),
        listPsaTicketLinks(),
      ]);
      setCatalog(Array.isArray(c) ? c : []);
      setConnections(conn);
      setEvents(ev);
      setLinks(lk);
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <ModuleShell title="PSA Integration" subtitle="ConnectWise, Autotask, Halo, Zendesk, and more">
      <Err error={error} />
      <div className="flex justify-end mb-4">
        <Btn variant="ghost" onClick={load}>
          Refresh
        </Btn>
      </div>
      <Panel title="Provider catalog">
        <DataTable
          columns={["Key", "Name"]}
          rows={catalog.map((x) => [x.provider_key || x.key, x.display_name || x.name])}
        />
      </Panel>
      <Panel title="Connections">
        <DataTable
          columns={["Name", "Provider", "Enabled", "Last sync"]}
          rows={connections.map((c) => [
            c.name || c.display_name,
            c.provider_key,
            String(c.enabled),
            c.last_sync_at,
          ])}
        />
      </Panel>
      <Panel title="Recent sync events">
        <DataTable
          columns={["Type", "Status", "Created"]}
          rows={events.slice(0, 30).map((e) => [e.event_type || e.type, e.status, e.created_at])}
        />
      </Panel>
      <Panel title="Ticket links">
        <DataTable
          columns={["Local ticket", "External ID", "Provider"]}
          rows={links.map((l) => [l.ticket_id, l.external_id, l.provider_key])}
        />
      </Panel>
    </ModuleShell>
  );
}
