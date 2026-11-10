import Link from 'next/link';
import { PageHero } from '@/shared/marketing/MarketingUI';

export const metadata = {
  title: 'Terms, refunds, cancellation and delivery — Bhudi & Cyber Bastion',
  description:
    'Terms and conditions for Cyber Bastion and Bhudi, including refund, cancellation, and delivery policies. One account and payment page for both websites.',
};

const ACCOUNT = 'https://www.bhudi.online/signup';

export default function TermsPage() {
  return (
    <>
      <PageHero
        label="Legal"
        title="Terms and conditions"
        subtitle="These terms cover Cyber Bastion (cyberbastion.co.za) and Bhudi (bhudi.online), including how you pay, how the service is delivered, how you cancel, and when you get a refund."
        primaryHref="/signup"
        primaryLabel="Create account"
        secondaryHref="/login"
        secondaryLabel="Sign in"
      />

      <article className="mx-auto max-w-3xl space-y-10 px-4 py-16 text-sm leading-relaxed text-slate-700 sm:px-6">
        <p className="text-xs uppercase tracking-wide text-slate-400">Last updated 10 November 2026</p>

        <section className="space-y-3" id="who">
          <h2 className="text-xl font-semibold text-slate-900">1. Who you are contracting with</h2>
          <p>
            Cyber Bastion provides cybersecurity services and operates Bhudi, the remote monitoring
            and management platform. These terms apply to both{' '}
            <a className="text-indigo-600 hover:underline" href="https://www.cyberbastion.co.za">
              cyberbastion.co.za
            </a>{' '}
            and{' '}
            <a className="text-indigo-600 hover:underline" href="https://www.bhudi.online">
              bhudi.online
            </a>
            , and to any quote, subscription, or online order accepted under either brand.
          </p>
          <p>
            Supplier contact: Cyber Bastion, Kempton Park, Gauteng, South Africa. Phone{' '}
            <a className="text-indigo-600 hover:underline" href="tel:+27790382171">
              +27 79 038 2171
            </a>
            . Email{' '}
            <a className="text-indigo-600 hover:underline" href="mailto:info@cyberbastion.co.za">
              info@cyberbastion.co.za
            </a>{' '}
            and{' '}
            <a className="text-indigo-600 hover:underline" href="mailto:info@bhudi.online">
              info@bhudi.online
            </a>
            .
          </p>
          <p>
            Nothing in these terms takes away a right you cannot waive under the Consumer Protection
            Act 68 of 2008 or the Electronic Communications and Transactions Act 25 of 2002.
          </p>
        </section>

        <section className="space-y-3" id="account">
          <h2 className="text-xl font-semibold text-slate-900">2. One account and one payment page</h2>
          <p>
            Cyber Bastion and Bhudi use a single customer account. Whether you start on
            cyberbastion.co.za or on bhudi.online, you create that account and sign in only at{' '}
            <a className="font-medium text-indigo-600 hover:underline" href={ACCOUNT}>
              www.bhudi.online/signup
            </a>{' '}
            (new customers) or{' '}
            <Link className="font-medium text-indigo-600 hover:underline" href="/login">
              www.bhudi.online/login
            </Link>{' '}
            (returning customers). Card and PayPal payments are taken only after you are signed in,
            on{' '}
            <Link className="font-medium text-indigo-600 hover:underline" href="/billing">
              www.bhudi.online/billing
            </Link>
            , through Stripe. cyberbastion.co.za does not run a separate checkout.
          </p>
        </section>

        <section className="space-y-3" id="services">
          <h2 className="text-xl font-semibold text-slate-900">3. What you are buying</h2>
          <p>
            Bhudi plans (Starter, Professional, and Enterprise) are monthly digital subscriptions for
            monitoring, remote support, ticketing, and related IT operations tools. Device limits and
            prices are the ones shown on the pricing page or in a written quote.
          </p>
          <p>
            Cyber Bastion professional services — including assessments, managed security, penetration
            testing, and incident response — are delivered under a quote or statement of work. Those
            services are not included in a Bhudi software subscription unless the quote says so.
          </p>
        </section>

        <section className="space-y-3" id="delivery">
          <h2 className="text-xl font-semibold text-slate-900">4. Delivery policy</h2>
          <p>
            Bhudi is software delivered electronically. There is no physical shipment unless a written
            statement of work says otherwise.
          </p>
          <ul className="list-disc space-y-2 pl-5">
            <li>
              After a successful payment, your subscription is attached to the account you signed in
              with. This usually happens within minutes, and no later than 3 business days.
            </li>
            <li>
              The endpoint agent is delivered as a download from the Bhudi portal (BhudiAgent-Setup.exe
              for Windows, plus the Linux and macOS builds where offered). You install it on the
              devices you manage.
            </li>
            <li>
              If we cannot give you portal access or the agent download within 3 business days of a
              successful payment, email us and we will either complete delivery or refund that charge
              in full.
            </li>
            <li>
              Professional services are delivered remotely or on site in Gauteng, as agreed in the
              quote. Delivery means the work has started on the agreed date, or the report or access
              described in the quote has been provided.
            </li>
          </ul>
        </section>

        <section className="space-y-3" id="cancellation">
          <h2 className="text-xl font-semibold text-slate-900">5. Cancellation policy</h2>
          <p>You can cancel in any of these ways:</p>
          <ul className="list-disc space-y-2 pl-5">
            <li>
              Email{' '}
              <a className="text-indigo-600 hover:underline" href="mailto:info@bhudi.online">
                info@bhudi.online
              </a>{' '}
              or{' '}
              <a className="text-indigo-600 hover:underline" href="mailto:info@cyberbastion.co.za">
                info@cyberbastion.co.za
              </a>{' '}
              from the address on the account. Include the account email and, if you have it, the
              invoice or payment reference.
            </li>
            <li>Or sign in and cancel the subscription from Billing before the next renewal date.</li>
          </ul>
          <p>
            Cancellation stops future renewal charges. Access continues until the end of the period
            you have already paid for, unless a cooling-off refund in section 6 applies.
          </p>
          <p>
            <strong>Electronic transactions.</strong> For a contract concluded electronically, you may
            cancel within 7 days of the date of the transaction under section 44 of the Electronic
            Communications and Transactions Act, except where that Act says the cooling-off right does
            not apply. It does not apply where you agreed that we could start the service during the
            cooling-off period and the service has already begun, or where software has been unsealed
            and the agent is already in production use beyond the initial install.
          </p>
          <p>
            <strong>Direct marketing.</strong> If you concluded the contract because of direct
            marketing, you may cancel it within 5 business days under section 16 of the Consumer
            Protection Act.
          </p>
          <p>
            <strong>Professional services.</strong> You may cancel a project before work starts and
            receive a full refund of amounts paid for that project. After work has started, you pay
            for work already performed and reasonable costs we have already committed, and we refund
            the rest of any prepayment.
          </p>
        </section>

        <section className="space-y-3" id="refunds">
          <h2 className="text-xl font-semibold text-slate-900">6. Refund policy</h2>
          <ul className="list-disc space-y-2 pl-5">
            <li>
              A cooling-off cancellation that qualifies under section 5 is refunded in full, to the
              original payment method, within 14 days of us receiving the cancellation.
            </li>
            <li>
              If we miss the 3-business-day delivery window in section 4 and you ask us to cancel, we
              refund the subscription charge in full.
            </li>
            <li>
              Duplicate charges, and payments that settled after a checkout you had already cancelled,
              are refunded in full.
            </li>
            <li>
              After the cooling-off period, fees for the current subscription period are not refunded.
              We simply do not charge the next period once you have cancelled.
            </li>
            <li>
              Incident response, penetration testing, or other professional work already performed is
              not refunded, except where the Consumer Protection Act requires a refund.
            </li>
            <li>
              Refunds are made in the currency you were charged (USD via Stripe, unless a quote states
              South African rand). Your bank may take additional time to show the credit.
            </li>
          </ul>
        </section>

        <section className="space-y-3" id="payment">
          <h2 className="text-xl font-semibold text-slate-900">7. Price and payment</h2>
          <p>
            Prices on the pricing page are monthly subscription fees in US dollars unless a quote says
            otherwise. Where South African VAT must be charged, it is added on top of the displayed
            price. Payment is by card or PayPal through Stripe on the shared billing page after you
            sign in. You authorise renewal charges until you cancel.
          </p>
        </section>

        <section className="space-y-3" id="law">
          <h2 className="text-xl font-semibold text-slate-900">8. Law</h2>
          <p>
            These terms are governed by the laws of the Republic of South Africa. If a clause is
            unenforceable, the rest still applies.
          </p>
          <p>
            Questions about a charge, a cancellation, or a refund:{' '}
            <a className="text-indigo-600 hover:underline" href="mailto:info@bhudi.online">
              info@bhudi.online
            </a>
            .
          </p>
        </section>
      </article>
    </>
  );
}
