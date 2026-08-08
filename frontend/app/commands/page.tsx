import ModuleShell from '@/shared/components/ModuleShell';
import CommandCenter from '@/shared/components/CommandCenter';

export default function CommandsPage() {
  return (
    <ModuleShell title="Command Center" subtitle="Run controlled endpoint operations from one workspace.">
      <CommandCenter />
    </ModuleShell>
  );
}
