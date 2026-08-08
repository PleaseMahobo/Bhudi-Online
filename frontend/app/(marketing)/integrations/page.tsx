import Link from 'next/link';

export const metadata = {
  title: 'Integrations — Bhudi',
  description: 'Security, print, identity, and cloud integrations for Bhudi.',
};

const GROUPS = [
  {
    title: 'Endpoint security',
    items: ['Microsoft Defender', 'CrowdStrike', 'Huntress', 'Bitdefender', 'Sophos', 'Malwarebytes', 'ThreatLocker'],
  },
  {
    title: 'Print ecosystem',
    items: ['Microsoft Print Server', 'Universal Print', 'UniPrint', 'Printix', 'PaperCut'],
  },
  {
    title: 'Identity & collaboration',
    items: ['Microsoft 365', 'Entra ID / Azure AD', 'SSO-ready enterprise auth'],
  },
  {
    title: 'Operations',
    items: ['Ticketing bridges', 'Webhook & API access', 'Script / automation runners'],
  },
];

export default function IntegrationsPage() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
      <div className="max-w-2xl">
        <p className="text-sm font-semibold text-indigo-600">Integrations</p>
        <h1 className="mt-2 text-4xl font-bold tracking-tight text-[#0F172A]">
          Connect the stack you already run
        </h1>
        <p className="mt-4 text-lg text-slate-600">
          Bhudi is provider-aware — not locked to a single vendor narrative. Bring
          your security, print, and identity tools into one operational picture.
        </p>
      </div>

      <div className="mt-14 grid gap-8 md:grid-cols-2">
        {GROUPS.map((g) => (
          <div key={g.title} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-900">{g.title}</h2>
            <ul className="mt-4 flex flex-wrap gap-2">
              {g.items.map((item) => (
                <li
                  key={item}
                  className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-sm text-slate-700"
                >
                  {item}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      <p className="mt-10 text-sm text-slate-600">
        Need something specific?{' '}
        <Link href="/contact" className="font-semibold text-indigo-600 hover:text-indigo-500">
          Contact us
        </Link>{' '}
        about roadmap integrations.
      </p>
    </div>
  );
}
