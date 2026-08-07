'use client';

import React, { useCallback, useEffect, useState } from 'react';
import ModuleShell, { Btn, DataTable, Err, Panel } from '@/shared/components/ModuleShell';
import {
  listReportCatalog,
  listReportRuns,
  listReportSchedules,
  listReportTemplates,
} from '@/lib/api-modules';

export default function ReportingPage() {
  const [catalog, setCatalog] = useState<any>(null);
  const [templates, setTemplates] = useState<any[]>([]);
  const [schedules, setSchedules] = useState<any[]>([]);
  const [runs, setRuns] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [c, t, s, r] = await Promise.all([
        listReportCatalog().catch(() => null),
        listReportTemplates(),
        listReportSchedules(),
        listReportRuns(40),
      ]);
      setCatalog(c);
      setTemplates(t);
      setSchedules(s);
      setRuns(r);
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <ModuleShell title="Reporting" subtitle="Templates, schedules, and run history">
      <Err error={error} />
      <div className="flex justify-end mb-4">
        <Btn variant="ghost" onClick={load}>
          Refresh
        </Btn>
      </div>
      {catalog && (
        <Panel title="Catalog">
          <pre className="text-xs text-zinc-300 whitespace-pre-wrap">
            {JSON.stringify(catalog, null, 2)}
          </pre>
        </Panel>
      )}
      <Panel title="Templates">
        <DataTable
          columns={["Name", "Code", "Category"]}
          rows={templates.map((t) => [t.name, t.code, t.category || t.report_type])}
        />
      </Panel>
      <Panel title="Schedules">
        <DataTable
          columns={["Name", "Cron", "Enabled"]}
          rows={schedules.map((s) => [s.name, s.cron || s.schedule, String(s.enabled)])}
        />
      </Panel>
      <Panel title="Recent runs">
        <DataTable
          columns={["Template", "Status", "Created"]}
          rows={runs.map((r) => [r.template_id || r.name, r.status, r.created_at])}
        />
      </Panel>
    </ModuleShell>
  );
}
