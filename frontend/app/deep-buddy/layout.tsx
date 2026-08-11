import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: {
    default: 'Deep Buddy',
    template: '%s · Deep Buddy',
  },
  description:
    'Deep Buddy is a tactical-class RMM for MSPs — clients, sites, agents, remote access, and automation.',
};

export default function DeepBuddyRootLayout({ children }: { children: React.ReactNode }) {
  return children;
}
