import ConsoleShell from '@/shared/deepbuddy/ConsoleShell';

export default function DeepBuddyConsoleLayout({ children }: { children: React.ReactNode }) {
  return <ConsoleShell>{children}</ConsoleShell>;
}
