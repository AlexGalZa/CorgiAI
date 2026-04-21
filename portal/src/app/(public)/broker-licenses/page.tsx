import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Broker Licenses | Corgi Insurance',
  description:
    'State-by-state list of Corgi Insurance producer licenses and registered entities.',
};

export default function BrokerLicensesPage() {
  return (
    <main className="max-w-[1100px] mx-auto px-4 sm:px-6 md:px-12 py-10 md:py-14 flex flex-col gap-8">
      <div className="flex flex-col gap-2">
        <span className="text-[11px] font-semibold text-muted tracking-normal leading-[1.2] uppercase">
          Legal
        </span>
        <h1 className="font-heading text-[28px] sm:text-[36px] font-medium text-heading tracking-[-1.152px] leading-none">
          Broker Licenses.
        </h1>
        <p className="text-sm text-muted">Last updated: placeholder date</p>
      </div>

      <div className="rounded-2xl border border-dashed border-border bg-surface px-5 py-4 text-sm text-muted">
        This page contains placeholder content pending legal review. The table
        below will be populated with verified license numbers and registered
        entities provided by our compliance team.
      </div>

      <section className="flex flex-col gap-3">
        <p className="text-sm leading-relaxed text-body">
          Corgi Insurance Services, Inc. and its licensed affiliates maintain
          producer licenses in the states listed below. For inquiries about a
          specific jurisdiction, contact{' '}
          <a
            href="mailto:hello@corgi.insure"
            className="text-primary hover:underline"
          >
            hello@corgi.insure
          </a>
          .
        </p>
      </section>

      <section className="flex flex-col gap-3">
        <div className="overflow-x-auto rounded-2xl border border-border bg-surface">
          <table className="w-full text-left text-sm">
            <thead className="bg-bg/50">
              <tr className="border-b border-border">
                <th
                  scope="col"
                  className="px-5 py-3 text-[11px] font-semibold text-muted tracking-normal uppercase"
                >
                  State
                </th>
                <th
                  scope="col"
                  className="px-5 py-3 text-[11px] font-semibold text-muted tracking-normal uppercase"
                >
                  License #
                </th>
                <th
                  scope="col"
                  className="px-5 py-3 text-[11px] font-semibold text-muted tracking-normal uppercase"
                >
                  Entity
                </th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td
                  colSpan={3}
                  className="px-5 py-10 text-center text-sm text-muted"
                >
                  Licenses pending &mdash; contact{' '}
                  <a
                    href="mailto:hello@corgi.insure"
                    className="text-primary hover:underline"
                  >
                    hello@corgi.insure
                  </a>
                  .
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="font-heading text-xl font-medium text-heading tracking-[-0.5px]">
          Verification
        </h2>
        <p className="text-sm leading-relaxed text-body">
          You may verify any producer license with the applicable state
          department of insurance or via the NAIC&rsquo;s National Insurance
          Producer Registry (NIPR). Placeholder copy pending legal review.
        </p>
      </section>
    </main>
  );
}
