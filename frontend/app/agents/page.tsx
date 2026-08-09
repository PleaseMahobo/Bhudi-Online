'use client';

import ModuleShell from '@/shared/components/ModuleShell';
import AgentInstallerPanel from '@/shared/components/AgentInstallerPanel';
import { Download, Monitor, ShieldCheck } from 'lucide-react';

export default function AgentsPage() {
  return (
    <ModuleShell>
      <div className="mx-auto max-w-4xl space-y-6 p-6">
        <header className="space-y-2">
          <div className="flex items-center gap-2 text-indigo-600">
            <Download size={22} />
            <span className="text-xs font-semibold uppercase tracking-wider">Agent deployment</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Download &amp; install agent</h1>
          <p className="max-w-2xl text-sm leading-relaxed text-slate-600">
            Install the native Bhudi agent on Windows, Linux, or macOS endpoints. No Python or other runtime is required
            on the target machine. After install, the device enrolls and appears under Devices.
          </p>
        </header>

        <div className="grid gap-3 sm:grid-cols-3">
          {[
            { icon: Monitor, title: 'Any OS', body: 'Windows MSI/EXE, Linux, and macOS binaries' },
            { icon: ShieldCheck, title: 'No runtime', body: 'Static native binary — nothing else to pre-install' },
            { icon: Download, title: 'Auto-enroll', body: 'Starts and registers with your Bhudi server' },
          ].map(({ icon: Icon, title, body }) => (
            <div key={title} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <Icon size={18} className="text-indigo-600" />
              <p className="mt-2 text-sm font-semibold text-slate-900">{title}</p>
              <p className="mt-1 text-xs text-slate-500">{body}</p>
            </div>
          ))}
        </div>

        <AgentInstallerPanel />

        <div className="rounded-xl border border-amber-100 bg-amber-50/80 px-4 py-3 text-xs text-amber-900">
          <p className="font-semibold">Tip</p>
          <p className="mt-1 leading-relaxed">
            Prefer <strong>Windows (.msi)</strong> for Intune or Group Policy. Use the EXE for a one-off machine. Linux
            and macOS use a single binary with an <code className="rounded bg-amber-100 px-1">install</code> command.
          </p>
        </div>
      </div>
    </ModuleShell>
  );
}
