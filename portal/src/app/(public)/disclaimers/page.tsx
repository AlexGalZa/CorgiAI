import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Disclaimers | Corgi Insurance',
  description:
    'Regulatory disclaimers, carrier notices, and brand references for Corgi Insurance.',
};

export default function DisclaimersPage() {
  return (
    <main className="max-w-[1100px] mx-auto px-4 sm:px-6 md:px-12 py-10 md:py-14 flex flex-col gap-8">
      <div className="flex flex-col gap-2">
        <span className="text-[11px] font-semibold text-muted tracking-normal leading-[1.2] uppercase">
          Legal
        </span>
        <h1 className="font-heading text-[28px] sm:text-[36px] font-medium text-heading tracking-[-1.152px] leading-none">
          Disclaimers.
        </h1>
        <p className="text-sm text-muted">Last updated: placeholder date</p>
      </div>

      <div className="rounded-2xl border border-dashed border-border bg-surface px-5 py-4 text-sm text-muted">
        This page contains placeholder content pending legal review. Exact
        wording, carrier attributions, and jurisdictional notices will be
        provided by counsel prior to public launch.
      </div>

      <section className="flex flex-col gap-3">
        <h2 className="font-heading text-xl font-medium text-heading tracking-[-0.5px]">
          References to &ldquo;Corgi&rdquo;
        </h2>
        <p className="text-sm leading-relaxed text-body">
          References to &ldquo;Corgi,&rdquo; &ldquo;Corgi Insurance,&rdquo;
          &ldquo;we,&rdquo; &ldquo;us,&rdquo; or &ldquo;our&rdquo; include Corgi
          Insurance Services, Inc. and its licensed affiliates operating as
          insurance producers in the United States. Specific products may be
          offered through a subsidiary or appointed carrier; in such cases the
          issuing entity is identified on the applicable policy documents.
          Placeholder copy.
        </p>
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="font-heading text-xl font-medium text-heading tracking-[-0.5px]">
          Not a policy
        </h2>
        <p className="text-sm leading-relaxed text-body">
          The information on this site is for general informational purposes and
          does not constitute an offer, solicitation, or contract of insurance.
          Coverage is subject to the terms, conditions, limitations, and
          exclusions of the actual policy issued. Placeholder copy.
        </p>
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="font-heading text-xl font-medium text-heading tracking-[-0.5px]">
          Quotes and estimates
        </h2>
        <p className="text-sm leading-relaxed text-body">
          Premium estimates displayed in the portal are indicative and may change
          based on underwriting review, carrier availability, and applicable
          state regulations. No coverage is bound until you receive written
          confirmation from Corgi or the issuing carrier. Placeholder copy.
        </p>
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="font-heading text-xl font-medium text-heading tracking-[-0.5px]">
          Licensing
        </h2>
        <p className="text-sm leading-relaxed text-body">
          Corgi is licensed as an insurance producer in the states in which it
          transacts business. For a full list of licenses, see our{' '}
          <Link href="/broker-licenses" className="text-primary hover:underline">
            broker licenses
          </Link>{' '}
          page.
        </p>
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="font-heading text-xl font-medium text-heading tracking-[-0.5px]">
          Third-party trademarks
        </h2>
        <p className="text-sm leading-relaxed text-body">
          Carrier names, logos, and product marks referenced on this site are
          the property of their respective owners and are used for identification
          purposes only. Placeholder copy.
        </p>
      </section>
    </main>
  );
}
