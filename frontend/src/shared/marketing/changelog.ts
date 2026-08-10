export type ChangelogEntry = {
  version: string;
  date: string;
  title: string;
  tags: string[];
  body: string[];
};

export const CHANGELOG: ChangelogEntry[] = [
  {
    version: '2.2.9',
    date: '2026-08-10',
    title: 'Persistent Windows install & marketing polish',
    tags: ['Agent', 'Website'],
    body: [
      'One-time Windows install: logon task, Run key, saved server config and identity.',
      'Contact form API with optional Resend email and CRM webhook delivery.',
      'Expanded public pages: features, solutions, docs, changelog, and blog.',
    ],
  },
  {
    version: '2.2.8',
    date: '2026-08-10',
    title: 'Accurate remote control & multi-monitor',
    tags: ['Remote'],
    body: [
      'Per-monitor capture with Display picker in Remote Access.',
      'Click mapping accounts for scaled frames (fixes Start-button offset).',
      'Fit page / fit width viewer without CSS transforms breaking hit tests.',
    ],
  },
  {
    version: '2.2.7',
    date: '2026-08-09',
    title: 'Display capture reliability',
    tags: ['Agent', 'Remote'],
    body: [
      'CreateDIBSection capture path to avoid GetDIBits failures.',
      'Monitor enumeration and region capture for multi-display PCs.',
    ],
  },
  {
    version: '2.2.0',
    date: '2026-08-08',
    title: 'Native agent & remote desktop',
    tags: ['Agent'],
    body: [
      'Native Go agent for Windows, Linux, and macOS — no Python on endpoints.',
      'WebSocket remote desktop streaming and terminal sessions.',
    ],
  },
];
