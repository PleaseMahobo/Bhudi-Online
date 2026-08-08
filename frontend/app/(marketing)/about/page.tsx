import Link from 'next/link';

export const metadata = {
  title: 'About — Bhudi',
  description: 'Why Bhudi exists and how we approach IT operations platforms.',
};

export default function AboutPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-16 sm:px-6">
      <p className="text-sm font-semibold text-indigo-600">About</p>
      <h1 className="mt-2 text-4xl font-bold tracking-tight text-[#0F172A]">
        IT operations with a point of view
      </h1>
      <div className="mt-8 space-y-5 text-slate-600 leading-relaxed">
        <p>
          Bhudi is an AI-powered IT operations platform for MSPs and enterprise
          teams. We believe operators deserve software that is as calm as it is
          capable — familiar workflows without becoming a near-clone of any one
          legacy console.
        </p>
        <p>
          Our product direction uses best-in-class RMM usability as inspiration,
          then builds a distinct Bhudi identity: Deep Navy and Indigo visual
          language, print management as a first-class citizen, and an AI assistant
          that stays docked in the work — not a separate chatbot tab.
        </p>
        <p>
          Monitor. Manage. Secure. That is the job. Bhudi is how we help teams do
          it with less noise and more signal.
        </p>
      </div>
      <Link
        href="/contact"
        className="mt-10 inline-flex rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500"
      >
        Get in touch
      </Link>
    </div>
  );
}
