'use client';

import React, { useCallback, useEffect, useState } from 'react';
import ModuleShell, { Btn, DataTable, Err, Panel } from '@/shared/components/ModuleShell';
import {
  getStripeBillingStatus,
  listBillingPlans,
  seedBillingPlans,
} from '@/lib/api-modules';

export default function BillingPage() {
  const [plans, setPlans] = useState<any[]>([]);
  const [stripe, setStripe] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [p, s] = await Promise.all([
        listBillingPlans(),
        getStripeBillingStatus().catch(() => ({ status: 'unavailable' })),
      ]);
      setPlans(p);
      setStripe(s);
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <ModuleShell title="Billing" subtitle="MSP plans and Stripe webhook integration status">
      <Err error={error} />
      <Panel
        title="Stripe"
        actions={
          <Btn variant="ghost" onClick={load}>
            Refresh
          </Btn>
        }
      >
        <pre className="text-xs text-sky-200 whitespace-pre-wrap bg-zinc-950 rounded-xl p-4 border border-zinc-800">
          {JSON.stringify(stripe, null, 2)}
        </pre>
      </Panel>
      <Panel
        title="Plans"
        actions={
          <Btn
            variant="ghost"
            onClick={() =>
              seedBillingPlans()
                .then(load)
                .catch((e) => setError(e.message))
            }
          >
            Seed defaults
          </Btn>
        }
      >
        <DataTable
          columns={["Code", "Name", "Monthly", "Active"]}
          rows={plans.map((p) => [
            p.code,
            p.name,
            p.price_monthly ?? p.unit_amount,
            String(p.active ?? p.is_active),
          ])}
        />
      </Panel>
    </ModuleShell>
  );
}
