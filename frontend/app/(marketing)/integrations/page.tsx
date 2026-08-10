import { PageHero, CtaBand, SectionLabel } from '@/shared/marketing/MarketingUI';

export const metadata = {
  title: 'Integrations — Bhudi',
  description: 'Security, print, identity, and cloud tools that fit into the Bhudi operations workspace.',
};

const GROUPS = [
  {
    title: 'Endpoint security',
    items: ['CrowdStrike', 'ThreatLocker', 'Huntress', 'Bitdefender', 'Sophos', 'Malwarebytes'],
  },
  {
    title: 'Print ecosystem',
    items: ['Microsoft Print Server', 'Universal Print', 'Printix', 'PaperCut', 'UniPrint'],
  },
  {
    title: 'Identity & access',
    items: ['Microsoft Entra ID (roadmap)', 'SSO / SAML (Enterprise)', 'Local workspace auth'],
  },
  {
    title: 'Cloud & ops',
    items: ['GitHub agent releases', 'Railway-hosted API', 'Webhooks (roadmap)', 'SIEM export (roadmap)'],
  },
];

export default function IntegrationsPage() {
  return (
    <>
      <PageHero
        label="Integrations"
        title="Meet the tools you already trust"
        subtitle="Bhudi is designed to sit at the center of operations — surface partner security signals, print stacks, and identity providers without forcing a rip-and-replace."
        primaryHref="/contact"
        primaryLabel="Request an integration"
        secondaryHref="/documentation"
        secondaryLabel="Developer docs"
      />

      <section className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <div className="grid gap-10 md:grid-cols-2">
          {GROUPS.map((g) => (
            <div key={g.title}>
              <SectionLabel>{g.title}</SectionLabel>
              <ul className="mt-4 grid gap-2 sm:grid-cols-2">
                {g.items.map((name) => (
                  <li
                    key={name}
                    className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-medium text-slate-800 shadow-sm"
                  >
                    {name}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <p className="mt-10 text-sm text-slate-500">
          Availability varies by plan and release channel. Tell us which connectors matter most for your estate.
        </p>
      </section>

      <CtaBand title="Need a connector we have not listed?" body="Contact us with your stack — we prioritize integrations used by active MSP and enterprise customers." />
    </>
  );
}
