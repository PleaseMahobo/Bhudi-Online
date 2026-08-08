import Link from 'next/link';

export const metadata = {
  title: 'Solutions — Bhudi',
  description: 'Bhudi for MSPs, enterprise IT, and hybrid security operations.',
};

const SOLUTIONS = [
  {
    title: 'Managed Service Providers',
    body: 'Multi-tenant visibility, shared runbooks, and AI that answers across customer estates — without drowning techs in noise.',
    points: ['Customer/tenant separation', 'Alert-to-ticket workflows', 'Print & endpoint coverage', 'Executive reporting'],
  },
  {
    title: 'Enterprise IT',
    body: 'One operations plane for servers, endpoints, printers, and security findings — with role-aware access and auditability.',
    points: ['Central device inventory', 'Patch & software control', 'Security score trends', 'Compliance-ready reports'],
  },
  {
    title: 'Security-forward teams',
    body: 'Correlate agent health, open findings, and operational alerts so response is coordinated, not fragmented across consoles.',
    points: ['Provider-agnostic posture', 'Finding lifecycle', 'AI-assisted triage', 'Escalation policies'],
  },
];

export default function SolutionsPage() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
      <div className="max-w-2xl">
        <p className="text-sm font-semibold text-indigo-600">Solutions</p>
        <h1 className="mt-2 text-4xl font-bold tracking-tight text-[#0F172A]">
          Built for the teams who keep business online
        </h1>
        <p className="mt-4 text-lg text-slate-600">
          Whether you manage dozens of customers or a single complex estate, Bhudi
          adapts to your operating model.
        </p>
      </div>

      <div className="mt-14 space-y-8">
        {SOLUTIONS.map((s) => (
          <div
            key={s.title}
            className="grid gap-8 rounded-2xl border border-slate-200 bg-white p-8 shadow-sm lg:grid-cols-2"
          >
            <div>
              <h2 className="text-2xl font-semibold text-slate-900">{s.title}</h2>
              <p className="mt-3 text-slate-600 leading-relaxed">{s.body}</p>
              <Link
                href="/contact"
                className="mt-6 inline-flex text-sm font-semibold text-indigo-600 hover:text-indigo-500"
              >
                Talk to us about this use case →
              </Link>
            </div>
            <ul className="grid gap-3 sm:grid-cols-2">
              {s.points.map((p) => (
                <li
                  key={p}
                  className="rounded-xl border border-slate-100 bg-slate-50 px-4 py-3 text-sm font-medium text-slate-800"
                >
                  {p}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
