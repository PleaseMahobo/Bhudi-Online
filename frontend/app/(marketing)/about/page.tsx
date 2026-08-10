import { PageHero, CtaBand, SectionLabel } from '@/shared/marketing/MarketingUI';

export const metadata = {
  title: 'About — Bhudi',
  description: 'Bhudi is an AI-powered IT operations platform for MSPs and enterprise IT teams.',
};

export default function AboutPage() {
  return (
    <>
      <PageHero
        label="About"
        title="IT operations deserve a modern shell"
        subtitle="Bhudi exists to give MSPs and internal IT one place to monitor, manage, and secure the estate — with AI that shortens investigation, not a clone of yesterday’s RMM."
        primaryHref="/contact"
        primaryLabel="Contact us"
        secondaryHref="/features"
        secondaryLabel="Explore features"
      />

      <section className="mx-auto max-w-3xl px-4 py-16 sm:px-6">
        <SectionLabel>Mission</SectionLabel>
        <p className="mt-4 text-lg leading-relaxed text-slate-700">
          Technicians should not need five browser tabs and a jump box ritual to answer
          a simple question about a device. Bhudi unifies devices, remote access, print,
          tickets, and security signals — then puts an assistant in the same chrome.
        </p>
        <p className="mt-4 leading-relaxed text-slate-600">
          We take inspiration from clean operational UX while building a distinct Bhudi
          identity: deep navy surfaces, indigo actions, and native agents that do not drag
          a Python runtime onto every PC.
        </p>

        <div className="mt-12 grid gap-6 sm:grid-cols-3">
          {[
            ['Clarity', 'Prioritize what matters without visual noise.'],
            ['Control', 'Remote and automate with audit-friendly actions.'],
            ['Intelligence', 'Ask Bhudi AI; get paths to resolution faster.'],
          ].map(([t, b]) => (
            <div key={t} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <h3 className="font-semibold text-[#0F172A]">{t}</h3>
              <p className="mt-2 text-sm text-slate-600">{b}</p>
            </div>
          ))}
        </div>
      </section>

      <CtaBand title="Build the next chapter with us" body="Whether you are piloting a site or partnering on delivery, we would like to hear from you." />
    </>
  );
}
