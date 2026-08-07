'use client';

import React, { useCallback, useEffect, useState } from 'react';
import ModuleShell, { Btn, DataTable, Err, Panel } from '@/shared/components/ModuleShell';
import {
  listComplianceAssessments,
  listComplianceFrameworks,
  listComplianceScores,
  seedComplianceFrameworks,
} from '@/lib/api-modules';

export default function CompliancePage() {
  const [frameworks, setFrameworks] = useState<any[]>([]);
  const [assessments, setAssessments] = useState<any[]>([]);
  const [scores, setScores] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [f, a, s] = await Promise.all([
        listComplianceFrameworks(),
        listComplianceAssessments(),
        listComplianceScores().catch(() => []),
      ]);
      setFrameworks(f);
      setAssessments(a);
      setScores(s);
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <ModuleShell title="Compliance" subtitle="Frameworks, assessments, continuous scores">
      <Err error={error} />
      <Panel
        title="Frameworks"
        actions={
          <div className="flex gap-2">
            <Btn
              variant="ghost"
              onClick={() =>
                seedComplianceFrameworks()
                  .then(load)
                  .catch((e) => setError(e.message))
              }
            >
              Seed
            </Btn>
            <Btn variant="ghost" onClick={load}>
              Refresh
            </Btn>
          </div>
        }
      >
        <DataTable
          columns={["Name", "Code", "Version"]}
          rows={frameworks.map((f) => [f.name, f.code, f.version])}
        />
      </Panel>
      <Panel title="Assessments">
        <DataTable
          columns={["Name", "Status", "Score"]}
          rows={assessments.map((a) => [
            a.name || a.title,
            a.status,
            a.score ?? a.overall_score,
          ])}
        />
      </Panel>
      <Panel title="Scores">
        <DataTable
          columns={["Target", "Score", "Updated"]}
          rows={scores.map((s) => [
            s.target_id || s.framework_id,
            s.score ?? s.value,
            s.updated_at || s.computed_at,
          ])}
        />
      </Panel>
    </ModuleShell>
  );
}
