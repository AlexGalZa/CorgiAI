'use client';

import { useState } from 'react';
import { usePageTitle } from '@/hooks/use-page-title';
import { useBillingInfo, useBillingPortal } from '@/hooks/use-billing';
import { useAppStore } from '@/stores/use-app-store';
import { Btn3DWhite } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Modal } from '@/components/ui/modal';
import { BillingIcon, CloseIcon, DownloadIcon } from '@/components/icons';
import { formatCurrency, formatDateLong } from '@/lib/utils';
import { apiFetch } from '@/lib/api';
import type { APIPaymentHistory } from '@/types';

function LoadingSkeleton() {
  return (
    <div className="max-w-[1100px] mx-auto px-4 sm:px-6 md:px-12 py-6 md:py-10 flex flex-col gap-6 md:gap-8 animate-pulse">
      <div className="flex items-end justify-between">
        <div className="flex flex-col gap-2">
          <div className="h-3 w-16 bg-border rounded" />
          <div className="h-8 w-48 bg-border rounded" />
        </div>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="h-20 bg-border rounded-2xl" />
        <div className="h-20 bg-border rounded-2xl" />
        <div className="h-20 bg-border rounded-2xl" />
      </div>
      <div className="h-40 bg-border rounded-2xl" />
      <div className="h-60 bg-border rounded-2xl" />
    </div>
  );
}

export default function BillingPage() {
  usePageTitle('Billing');
  const { data: billing, isLoading, isError, refetch } = useBillingInfo();
  const billingPortal = useBillingPortal();
  const { showToast } = useAppStore();
  const [selectedPayment, setSelectedPayment] = useState<APIPaymentHistory | null>(null);
  const [downloadingInvoice, setDownloadingInvoice] = useState<string | null>(null);
  const [switchingBilling, setSwitchingBilling] = useState(false);

  const handleDownloadInvoice = async (payment: APIPaymentHistory, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    if (payment.status !== 'succeeded') return;

    setDownloadingInvoice(payment.id);
    try {
      const data = await apiFetch<{ hosted_invoice_url: string }>(
        `/api/v1/stripe/invoice/${payment.id}/url`
      );
      if (data.hosted_invoice_url) {
        window.open(data.hosted_invoice_url, '_blank');
      } else {
        showToast('Invoice not available');
      }
    } catch {
      // Fallback: if API endpoint doesn't exist yet, try the invoice_url
      if (payment.invoice_url) {
        window.open(payment.invoice_url, '_blank');
      } else {
        showToast('Invoice not available for this payment');
      }
    } finally {
      setDownloadingInvoice(null);
    }
  };

  const handleChangePayment = () => {
    billingPortal.mutate(undefined, {
      onSuccess: (result) => {
        window.open(result.url, '_blank');
      },
      onError: (error) => {
        showToast(`Error: ${error.message}`);
      },
    });
  };

  if (isLoading) return <LoadingSkeleton />;

  if (isError) {
    return (
      <div className="max-w-[1100px] mx-auto px-4 sm:px-6 md:px-12 py-6 md:py-10 flex flex-col gap-6 md:gap-8">
        <div className="flex items-end justify-between">
          <div className="flex flex-col gap-1">
            <span className="text-[11px] font-semibold text-muted tracking-normal leading-[1.2] uppercase">Billing</span>
            <h1 className="font-heading text-[26px] sm:text-[32px] font-medium text-heading tracking-[-1.024px] leading-none">
              Payments &amp; Invoices
            </h1>
          </div>
        </div>
        <div className="flex flex-col items-center gap-4 pt-12">
          <div className="text-sm text-muted">Failed to load billing info.</div>
          <button
            onClick={() => refetch()}
            className="inline-flex items-center gap-1.5 text-sm font-medium text-primary bg-transparent border border-primary rounded-xl px-4 py-2 cursor-pointer hover:bg-primary hover:text-white transition-colors focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const hasBilling = billing?.has_billing ?? false;

  return (
    <div className="max-w-[1100px] mx-auto px-4 sm:px-6 md:px-12 py-6 md:py-10 flex flex-col gap-6 md:gap-8">
      {/* Page header */}
      <div className="flex items-end justify-between">
        <div className="flex flex-col gap-1">
          <span className="text-[11px] font-semibold text-muted tracking-normal leading-[1.2] uppercase">
            Billing
          </span>
          <h1 className="font-heading text-[26px] sm:text-[32px] font-medium text-heading tracking-[-1.024px] leading-none">
            Payments &amp; Invoices
          </h1>
        </div>
      </div>

      {!hasBilling ? (
        <div className="border border-dashed border-border rounded-2xl text-center py-16 px-10">
          <div className="mb-4 mx-auto w-12 h-12 flex items-center justify-center">
            <BillingIcon className="w-6 h-6 stroke-muted" />
          </div>
          <div className="text-sm font-medium text-heading mb-1">No billing provider configured</div>
          <div className="text-[13px] text-muted leading-[1.5] max-w-sm mx-auto">
            A billing provider (e.g. Stripe) hasn&apos;t been set up yet. Payment details and invoices will appear here once billing is configured and you have an active policy.
          </div>
        </div>
      ) : (
        <>
          {/* Stats strip */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4">
            <div className="bg-surface border border-border rounded-2xl px-5 py-4 flex flex-col gap-1">
              <div className="text-[11px] font-semibold text-muted uppercase tracking-[0.3px] leading-[1.2]">Current plan</div>
              <div className="text-xl font-medium text-heading tracking-[-0.5px] leading-none">
                {billing?.plans && billing.plans.length > 0
                  ? formatCurrency(billing.plans.reduce((sum, p) => sum + p.amount, 0)) + '/yr'
                  : '—'}
              </div>
            </div>
            <div className="bg-surface border border-border rounded-2xl px-5 py-4 flex flex-col gap-1">
              <div className="text-[11px] font-semibold text-muted uppercase tracking-[0.3px] leading-[1.2]">Next payment</div>
              <div className="text-xl font-medium text-heading tracking-[-0.5px] leading-none">
                {billing?.plans?.[0]?.next_payment_date
                  ? formatDateLong(new Date(billing.plans[0].next_payment_date))
                  : '—'}
              </div>
            </div>
            <div className="bg-surface border border-border rounded-2xl px-5 py-4 flex flex-col gap-1">
              <div className="text-[11px] font-semibold text-muted uppercase tracking-[0.3px] leading-[1.2]">Payment method</div>
              <div className="text-xl font-medium text-heading tracking-[-0.5px] leading-none">
                {billing?.payment_method
                  ? `•••• ${billing.payment_method.last4}`
                  : 'None'}
              </div>
            </div>
          </div>

          {/* Payment Plans */}
          {billing?.plans && billing.plans.length > 0 && (
            <div className="bg-surface border border-border rounded-2xl overflow-hidden">
              <div className="px-6 py-5">
                <span className="font-heading text-2xl font-normal text-heading tracking-[-0.768px] leading-none">
                  Payment Plans
                </span>
              </div>
              <div className="px-6 pb-5 flex flex-col gap-3">
                {/* Annual upsell for monthly plans */}
                {billing.plans.some((p) => p.billing_frequency === 'monthly') && (
                  <div className="border border-primary/30 bg-primary/5 rounded-xl p-4 flex items-center justify-between">
                    <div className="flex flex-col gap-1">
                      <span className="text-sm font-semibold text-heading">Save 10% by switching to Annual</span>
                      <span className="text-[11px] text-muted">Pay once a year and keep more in your pocket.</span>
                    </div>
                    <button
                      onClick={async () => {
                        setSwitchingBilling(true);
                        try {
                          const result = await apiFetch<{
                            frequency: string;
                            amount_charged_cents?: number;
                            discount_percent?: number;
                            subscription_id?: string;
                          }>('/api/v1/stripe/switch-billing-frequency', {
                            method: 'POST',
                            body: { frequency: 'annual' },
                          });
                          showToast('Switched to annual billing — 10% discount applied!');
                          refetch();
                        } catch (error) {
                          const msg = error instanceof Error ? error.message : 'Unknown error';
                          showToast(`Failed to switch: ${msg}`);
                        } finally {
                          setSwitchingBilling(false);
                        }
                      }}
                      disabled={switchingBilling}
                      className="shrink-0 inline-flex items-center justify-center bg-primary text-white text-sm font-semibold rounded-xl px-5 py-2.5 cursor-pointer border-none hover:bg-primary-dark transition-colors disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none"
                    >
                      {switchingBilling ? 'Switching...' : 'Switch to Annual'}
                    </button>
                  </div>
                )}
                {billing.plans.map((plan) => (
                  <div key={plan.policy_number} className="bg-bg border border-border rounded-xl p-4 flex items-center justify-between">
                    <div className="flex flex-col gap-1">
                      <span className="text-sm font-semibold text-heading">{plan.coverage_type}</span>
                      <span className="text-[11px] text-muted">{plan.policy_number} · {plan.billing_frequency}</span>
                    </div>
                    <div className="flex flex-col items-end gap-0.5">
                      <span className="text-sm font-semibold text-heading">
                        {formatCurrency(plan.amount)}/{plan.billing_frequency === 'monthly' ? 'mo' : 'yr'}
                      </span>
                      {plan.next_payment_date && (
                        <span className="text-[11px] text-muted">
                          Next: {formatDateLong(new Date(plan.next_payment_date))}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Billing Address */}
          <div className="bg-surface border border-border rounded-2xl overflow-hidden">
            <div className="flex items-center justify-between px-6 py-5">
              <span className="font-heading text-2xl font-normal text-heading tracking-[-0.768px] leading-none">
                Billing Address
              </span>
              <button
                onClick={() => {
                  // Redirect to Stripe Billing Portal for address management
                  billingPortal.mutate(undefined, {
                    onSuccess: (result) => {
                      window.open(result.url, '_blank');
                    },
                    onError: () => {
                      showToast('Billing address can be updated in Organization settings');
                    },
                  });
                }}
                disabled={billingPortal.isPending}
                className="inline-flex items-center gap-1.5 text-sm font-medium text-primary bg-transparent border-none cursor-pointer hover:underline p-0 disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none"
              >
                {billingPortal.isPending ? 'Loading...' : 'Update'}
              </button>
            </div>
            <div className="px-6 pb-5">
              <span className="text-sm text-muted">No billing address on file</span>
            </div>
          </div>

          {/* Payment History */}
          {billing?.history && billing.history.length > 0 && (
            <div className="flex flex-col gap-3">
              <div className="pl-4 text-[11px] font-semibold text-muted tracking-normal leading-[1.2] uppercase">
                Payment history
              </div>
              <div className="bg-surface border border-border rounded-2xl overflow-hidden">
                {/* Desktop table header — hidden on mobile */}
                <div className="hidden md:grid grid-cols-[minmax(200px,3fr)_100px_100px_60px_120px_110px] px-6 py-3 bg-bg border-b border-border">
                  <div className="text-[11px] font-semibold text-muted uppercase tracking-[0.3px]">Invoice</div>
                  <div className="text-[11px] font-semibold text-muted uppercase tracking-[0.3px] text-right">Amount</div>
                  <div className="text-[11px] font-semibold text-muted uppercase tracking-[0.3px] text-right">Status</div>
                  <div className="text-[11px] font-semibold text-muted uppercase tracking-[0.3px] text-center">PDF</div>
                  <div className="text-[11px] font-semibold text-muted uppercase tracking-[0.3px] text-right" />
                  <div className="text-[11px] font-semibold text-muted uppercase tracking-[0.3px] text-right">Date</div>
                </div>
                {billing.history.map((payment) => (
                  <div
                    key={payment.id}
                    onClick={() => setSelectedPayment(payment)}
                    className="border-b border-border last:border-b-0 hover:bg-bg transition-colors cursor-pointer"
                  >
                    {/* Desktop row */}
                    <div className="hidden md:grid grid-cols-[minmax(200px,3fr)_100px_100px_60px_120px_110px] px-6 py-4 items-center">
                      <div className="flex items-center gap-3 min-w-0">
                        <div className="w-10 h-10 bg-bg rounded-xl flex items-center justify-center shrink-0">
                          <BillingIcon className="w-5 h-5 stroke-muted" />
                        </div>
                        <div className="min-w-0">
                          <div className="text-sm font-semibold text-heading truncate">{payment.description || 'Payment'}</div>
                          <div className="text-[11px] text-muted truncate">
                            {payment.invoice_url ? 'Invoice available' : 'Payment processed'}
                          </div>
                        </div>
                      </div>
                      <div className="text-sm font-medium text-heading text-right">
                        {formatCurrency(payment.amount / 100)}
                      </div>
                      <div className="flex justify-end">
                        <Badge variant={payment.status === 'succeeded' ? 'active' : payment.status === 'pending' ? 'pending' : 'expired'} />
                      </div>
                      <div className="flex justify-center">
                        {payment.status === 'succeeded' && (
                          <button
                            onClick={(e) => handleDownloadInvoice(payment, e)}
                            disabled={downloadingInvoice === payment.id}
                            title="Download Invoice PDF"
                            className="w-8 h-8 flex items-center justify-center rounded-lg bg-transparent border border-border cursor-pointer hover:bg-bg transition-colors disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none"
                          >
                            {downloadingInvoice === payment.id ? (
                              <svg className="w-4 h-4 animate-spin text-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <path d="M12 2v4m0 12v4m-7.07-3.93l2.83-2.83m8.48-8.48l2.83-2.83M2 12h4m12 0h4m-3.93 7.07l-2.83-2.83M7.76 7.76L4.93 4.93" />
                              </svg>
                            ) : (
                              <DownloadIcon size={14} />
                            )}
                          </button>
                        )}
                      </div>
                      <div className="flex flex-col items-end gap-1">
                        {(payment.status === 'failed' || payment.status === 'past_due') && (
                          <>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                billingPortal.mutate(undefined, {
                                  onSuccess: (result) => {
                                    window.open(result.url, '_blank');
                                  },
                                  onError: () => {
                                    showToast('Unable to open billing portal. Please contact support.');
                                  },
                                });
                              }}
                              disabled={billingPortal.isPending}
                              className="inline-flex items-center justify-center bg-primary text-white text-[11px] font-semibold rounded-lg px-3 py-1.5 cursor-pointer border-none hover:bg-primary-dark transition-colors disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none"
                            >
                              {billingPortal.isPending ? '...' : 'Retry Payment'}
                            </button>
                            <a
                              href="mailto:support@corgiinsure.com"
                              className="text-[10px] text-primary hover:underline focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none rounded"
                              onClick={(e) => e.stopPropagation()}
                            >
                              Contact support
                            </a>
                          </>
                        )}
                      </div>
                      <div className="text-sm text-body text-right">
                        {formatDateLong(new Date(payment.created_at))}
                      </div>
                    </div>
                    {/* Mobile card layout */}
                    <div className="md:hidden px-4 py-4 flex flex-col gap-3">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-bg rounded-xl flex items-center justify-center shrink-0">
                          <BillingIcon className="w-5 h-5 stroke-muted" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-semibold text-heading truncate">{payment.description || 'Payment'}</div>
                          <div className="text-[11px] text-muted">{formatDateLong(new Date(payment.created_at))}</div>
                        </div>
                        <Badge variant={payment.status === 'succeeded' ? 'active' : payment.status === 'pending' ? 'pending' : 'expired'} />
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-heading">{formatCurrency(payment.amount / 100)}</span>
                        <div className="flex items-center gap-2">
                          {payment.status === 'succeeded' && (
                            <button
                              onClick={(e) => handleDownloadInvoice(payment, e)}
                              disabled={downloadingInvoice === payment.id}
                              className="inline-flex items-center justify-center gap-1 bg-surface border border-border text-[11px] font-medium text-heading rounded-lg px-2.5 py-1.5 cursor-pointer hover:bg-bg transition-colors disabled:opacity-50"
                            >
                              <DownloadIcon size={12} /> Invoice
                            </button>
                          )}
                          {(payment.status === 'failed' || payment.status === 'past_due') && (
                            <div className="flex flex-col items-end gap-1">
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  billingPortal.mutate(undefined, {
                                    onSuccess: (result) => { window.open(result.url, '_blank'); },
                                    onError: () => { showToast('Unable to open billing portal. Please contact support.'); },
                                  });
                                }}
                                disabled={billingPortal.isPending}
                                className="inline-flex items-center justify-center bg-primary text-white text-[11px] font-semibold rounded-lg px-3 py-1.5 cursor-pointer border-none hover:bg-primary-dark transition-colors disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none"
                              >
                                {billingPortal.isPending ? '...' : 'Retry'}
                              </button>
                              <a
                                href="mailto:support@corgiinsure.com"
                                className="text-[10px] text-primary hover:underline focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none rounded"
                                onClick={(e) => e.stopPropagation()}
                              >
                                Contact support
                              </a>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Payment Method Card */}
          <div className="bg-surface border border-border rounded-2xl overflow-hidden">
            <div className="flex items-center justify-between px-6 py-5">
              <span className="font-heading text-2xl font-normal text-heading tracking-[-0.768px] leading-none">
                Payment Method
              </span>
              <Btn3DWhite onClick={handleChangePayment}>
                {billingPortal.isPending ? 'Loading...' : 'Change payment method'}
              </Btn3DWhite>
            </div>
            <div className="px-6 pb-5">
              {billing?.payment_method ? (
                <div className="flex items-center gap-3">
                  <div className="w-10 h-7 bg-heading rounded flex items-center justify-center text-white text-[10px] font-bold uppercase">
                    {billing.payment_method.brand}
                  </div>
                  <div className="flex flex-col gap-0.5">
                    <span className="text-sm font-medium text-heading">
                      •••• {billing.payment_method.last4}
                    </span>
                    <span className="text-[11px] text-muted">
                      Expires {billing.payment_method.exp_month}/{billing.payment_method.exp_year}
                    </span>
                  </div>
                </div>
              ) : (
                <span className="text-sm text-muted">No payment method on file</span>
              )}
            </div>
          </div>
        </>
      )}

      {/* Payment Detail Modal */}
      <Modal open={!!selectedPayment} onClose={() => setSelectedPayment(null)} width={440}>
        {selectedPayment && (
          <div className="p-6 flex flex-col gap-5">
            <div className="flex items-start justify-between">
              <div className="font-heading text-2xl font-normal text-heading tracking-[-0.768px] leading-none">
                Payment Details
              </div>
              <button onClick={() => setSelectedPayment(null)} className="bg-transparent border-none cursor-pointer p-0 leading-none shrink-0 focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none rounded">
                <CloseIcon />
              </button>
            </div>

            <div className="border border-border rounded-lg overflow-hidden">
              <div className="flex items-center justify-between">
                <div className="p-3 text-sm font-normal text-body w-36 shrink-0">Amount</div>
                <div className="p-3 text-sm font-medium text-heading tracking-[-0.21px] text-right">
                  {formatCurrency(selectedPayment.amount / 100)}
                </div>
              </div>
              <div className="flex items-center justify-between border-t border-border">
                <div className="p-3 text-sm font-normal text-body w-36 shrink-0">Status</div>
                <div className="p-3">
                  <Badge variant={selectedPayment.status === 'succeeded' ? 'active' : 'pending'} />
                </div>
              </div>
              <div className="flex items-center justify-between border-t border-border">
                <div className="p-3 text-sm font-normal text-body w-36 shrink-0">Date</div>
                <div className="p-3 text-sm font-medium text-heading tracking-[-0.21px] text-right">
                  {formatDateLong(new Date(selectedPayment.created_at))}
                </div>
              </div>
              {selectedPayment.description && (
                <div className="flex items-center justify-between border-t border-border">
                  <div className="p-3 text-sm font-normal text-body w-36 shrink-0">Description</div>
                  <div className="p-3 text-sm font-medium text-heading tracking-[-0.21px] text-right">{selectedPayment.description}</div>
                </div>
              )}
            </div>

            <div className="flex gap-3">
              {selectedPayment.invoice_url && (
                <a
                  href={selectedPayment.invoice_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-1 flex items-center justify-center gap-2 bg-surface border border-border rounded-xl px-4 py-2.5 text-sm font-medium text-heading hover:bg-bg transition-colors no-underline focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none"
                >
                  View Invoice
                </a>
              )}
              {selectedPayment.status === 'succeeded' && (
                <button
                  onClick={() => handleDownloadInvoice(selectedPayment)}
                  disabled={downloadingInvoice === selectedPayment.id}
                  className="flex-1 flex items-center justify-center gap-2 bg-primary text-white border-none rounded-xl px-4 py-2.5 text-sm font-semibold cursor-pointer hover:bg-primary-dark transition-colors disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none"
                >
                  <DownloadIcon size={14} />
                  {downloadingInvoice === selectedPayment.id ? 'Loading...' : 'Download PDF'}
                </button>
              )}
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
