'use client';

import React, { useCallback, useEffect, useState } from 'react';
import ModuleShell, { Btn, DataTable, Err, Panel } from '@/shared/components/ModuleShell';
import {
  aiCapacityForecast,
  aiGenerateScript,
  aiKnowledgeSearch,
  aiPredictiveFailure,
  aiRemediation,
  aiRootCause,
  aiTicketSummary,
  listAiRuns,
} from '@/lib/api-modules';

export default function AiPage() {
  const [runs, setRuns] = useState<any[]>([]);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [title, setTitle] = useState('High CPU on host');
  const [symptoms, setSymptoms] = useState('CPU 98%, disk full alerts');
  const [goal, setGoal] = useState('List top processes by CPU');
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setRuns(await listAiRuns(undefined, 30));
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const run = async (fn: () => Promise<any>) => {
    setBusy(true);
    setError(null);
    try {
      const r = await fn();
      setResult(r);
      await load();
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <ModuleShell title="AI Console" subtitle="Root cause, scripts, remediation, forecasts, knowledge">
      <Err error={error} />
      <Panel title="Inputs">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
          <input
            className="bg-zinc-950 border border-zinc-700 rounded-xl px-3 py-2 text-sm"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Title / issue"
          />
          <input
            className="bg-zinc-950 border border-zinc-700 rounded-xl px-3 py-2 text-sm"
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            placeholder="Script goal"
          />
        </div>
        <textarea
          className="w-full bg-zinc-950 border border-zinc-700 rounded-xl px-3 py-2 text-sm min-h-[70px] mb-3"
          value={symptoms}
          onChange={(e) => setSymptoms(e.target.value)}
        />
        <div className="flex flex-wrap gap-2">
          <Btn
            onClick={() =>
              run(() => aiRootCause({ title, symptoms }))
            }
          >
            Root cause
          </Btn>
          <Btn
            onClick={() => run(() => aiGenerateScript({ goal, platform: 'powershell' }))}
          >
            Generate script
          </Btn>
          <Btn onClick={() => run(() => aiRemediation({ issue: title }))}>Remediation</Btn>
          <Btn
            onClick={() =>
              run(() =>
                aiTicketSummary({ title, description: symptoms, work_notes: [] })
              )
            }
          >
            Ticket summary
          </Btn>
          <Btn onClick={() => run(() => aiKnowledgeSearch(symptoms, 5))}>KB search</Btn>
          <Btn
            onClick={() =>
              run(() =>
                aiPredictiveFailure({
                  target_id: 'demo-device',
                  metrics: { cpu_pct: 92, disk_pct: 88 },
                })
              )
            }
          >
            Predictive
          </Btn>
          <Btn
            onClick={() =>
              run(() =>
                aiCapacityForecast({
                  resource: 'disk',
                  history: [{ value: 60 }, { value: 70 }, { value: 82 }],
                })
              )
            }
          >
            Capacity
          </Btn>
          {busy && <span className="text-sm text-zinc-400 self-center">Running…</span>}
        </div>
      </Panel>

      <Panel title="Last result">
        <pre className="text-xs text-sky-200 whitespace-pre-wrap break-all bg-zinc-950 rounded-xl p-4 border border-zinc-800 max-h-80 overflow-auto">
          {result ? JSON.stringify(result, null, 2) : 'Run an action to see output'}
        </pre>
      </Panel>

      <Panel title="Recent AI runs">
        <DataTable
          columns={["Type", "Status", "Model", "Latency", "Created"]}
          rows={runs.map((r) => [
            r.task_type,
            r.status,
            r.model,
            r.latency_ms != null ? `${r.latency_ms}ms` : null,
            r.created_at,
          ])}
        />
      </Panel>
    </ModuleShell>
  );
}
