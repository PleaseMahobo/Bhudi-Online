export type BlogPost = {
  slug: string;
  title: string;
  date: string;
  excerpt: string;
  tags: string[];
  body: string[];
};

export const BLOG_POSTS: BlogPost[] = [
  {
    slug: 'why-native-agents-matter',
    title: 'Why native agents matter for MSP fleets',
    date: '2026-08-08',
    excerpt:
      'Python runtimes on every endpoint look convenient until you manage ten thousand of them. Here is why Bhudi ships static native agents.',
    tags: ['Agents', 'MSP'],
    body: [
      'Managed service providers do not need another dependency chain on customer PCs. A native agent installs once, starts at logon, and reconnects after reboot without asking technicians to maintain Python on every site.',
      'Bhudi’s Windows, Linux, and macOS agents enroll against the runtime API, persist identity on disk, and stream remote desktop from the interactive user session.',
      'If you are piloting remote access, start with a small device set, confirm heartbeats, then expand.',
    ],
  },
  {
    slug: 'remote-control-that-fits-the-page',
    title: 'Remote control that fits the page (and the Start button)',
    date: '2026-08-10',
    excerpt:
      'Multi-monitor capture, fit-to-page viewing, and coordinate mapping that respects scaled frames.',
    tags: ['Remote', 'Product'],
    body: [
      'Bhudi lets you pick Display 1 or Display 2, then maps clicks from the viewer back through the scaled JPEG to native screen coordinates.',
      'Fit page uses max-width and max-height instead of CSS transforms, so hit-testing stays aligned with what you see.',
    ],
  },
  {
    slug: 'print-as-a-first-class-module',
    title: 'Print as a first-class operations module',
    date: '2026-07-22',
    excerpt:
      'Queues, drivers, and offline printers belong next to devices and tickets — not in a forgotten spreadsheet.',
    tags: ['Print', 'MSP'],
    body: [
      'Print still drives a large share of desk-side tickets. Treating servers, queues, toner, and offline devices as first-class objects in the same shell as RMM reduces context switching.',
      'Bhudi’s roadmap keeps vendor awareness (Universal Print, PaperCut, Printix, and classic Windows print servers) adjacent to the same estate view.',
    ],
  },
];

export function getPost(slug: string) {
  return BLOG_POSTS.find((p) => p.slug === slug);
}
