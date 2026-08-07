'use client';

import React, { useCallback, useEffect, useState } from 'react';
import ModuleShell, { Btn, DataTable, Err, Panel } from '@/shared/components/ModuleShell';
import {
  getBackupSummary,
  listBackupCatalog,
  listBackupJobs,
  listBackupProviders,
  listBackupResources,
  listBackupRestores,
  seedBackupProviders,
} from '@/lib/api-modules';

export default function BackupPage() {
  const [catalog, setCatalog] = useState<any[]>([]);
  const [providers, setProviders] = useState<any[]>([]);
  const [resources, setResources] = useState<any[]>([]);
  const [jobs, setJobs] = useState<any[]>([]);
  const [restores, setRestores] = useState<any[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [c, p, r, j, rest, sum] = await Promise.all([
        listBackupCatalog(),
        listBackupProviders(),
        listBackupResources(),
        listBackupJobs(),
        listBackupRestores(),
        getBackupSummary().catch(() => null),
      ]);
      setCatalog(c);
      setProviders(p);
      setResources(r);
      setJobs(j);
      setRestores(rest);
      setSummary(sum);
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <ModuleShell title="Backup Integration" subtitle="Providers, protected resources, jobs, restores">
      <Err error={error} />
      <Panel
        title="Fleet summary"
        actions={
          <div className="flex gap-2">
            <Btn
              variant="ghost"
              onClick={() =>
                seedBackupProviders()
                  .then(load)
                  .catch((e) => setError(e.message))
              }
            >
              Seed providers
            </Btn>
            <Btn variant="ghost" onClick={load}>
              Refresh
            </Btn>
          </div>
        }
      >
        {summary ? (
          <pre className="text-xs text-zinc-300 whitespace-pre-wrap">
            {JSON.stringify(summary, null, 2)}
          </pre>
        ) : (
          <p className="text-sm text-zinc-500">No summary yet</p>
        )}
      </Panel>
      <Panel title="Catalog">
        <DataTable
          columns={["Key", "Name"]}
          rows={catalog.map((x) => [x.provider_key || x.key, x.display_name || x.name])}
        />
      </Panel>
      <Panel title="Providers">
        <DataTable
          columns={["Name", "Key", "Enabled"]}
          rows={providers.map((p) => [p.display_name || p.name, p.provider_key, String(p.enabled)])}
        />
      </Panel>
      <Panel title="Protected resources">
        <DataTable
          columns={["Name", "Status", "Provider"]}
          rows={resources.map((r) => [r.name, r.status, r.provider_key || r.provider_id])}
        />
      </Panel>
      <Panel title="Jobs">
        <DataTable
          columns={["Type", "Status", "Started"]}
          rows={jobs.map((j) => [j.job_type || j.name, j.status, j.started_at || j.created_at])}
        />
      </Panel>
      <Panel title="Restores">
        <DataTable
          columns={["Status", "Device", "Created"]}
          rows={restores.map((r) => [r.status, r.device_id, r.created_at])}
        />
      </Panel>
    </ModuleShell>
  );
}
