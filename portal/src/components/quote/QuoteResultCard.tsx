'use client';

import { useState } from 'react';
import { Btn3DOrange } from '@/components/ui/button';
import { ArrowRightIcon, CheckIcon, CloseIcon } from '@/components/icons';
import { AllCoveragesInfo, type AllCoverageType } from '@/lib/quote-flow';
import { formatCurrency } from '@/lib/utils';
import type { BillingFrequency, RatingResult, CustomProduct } from '@/hooks/use-quote';

interface Props {
  isLoading: boolean;
  needsReview: boolean;
  totalMonthly: number;
  totalAnnual: number;
  billingFrequency: BillingFrequency;
  onBillingFrequencyChange: (f: BillingFrequency) => void;
  quoteNumber: string;
  selectedCoverages: AllCoverageType[];
  customProducts: CustomProduct[];
  ratingResult?: RatingResult | null;
  effectiveDate?: Date;
  hasUnsavedChanges: boolean;
  canCheckout: boolean;
  onCheckout: () => void;
  promoCode?: string | null;
  discountPercentage?: number | null;
  discountMonthly?: number | null;
  discountAnnual?: number | null;
  onApplyPromoCode: (code: string) => void;
  onRemovePromoCode: () => void;
}

export function QuoteResultCard({
  isLoading,
  needsReview,
  totalMonthly,
  totalAnnual,
  billingFrequency,
  onBillingFrequencyChange,
  quoteNumber,
  selectedCoverages,
  customProducts,
  ratingResult,
  effectiveDate,
  hasUnsavedChanges,
  canCheckout,
  onCheckout,
  promoCode,
  discountPercentage,
  discountMonthly,
  discountAnnual,
  onApplyPromoCode,
  onRemovePromoCode,
}: Props) {
  const [promoInput, setPromoInput] = useState('');
  const [showPromo, setShowPromo] = useState(false);
  const isMonthly = billingFrequency === 'monthly';
  const hasAmount = totalMonthly > 0;
  const showPricing = hasAmount && canCheckout;
  const hasActivePromo = !!promoCode && !!discountPercentage;

  const getCoveragePrice = (id: AllCoverageType) => {
    if (!ratingResult?.coverages?.[id]) return 0;
    return isMonthly ? ratingResult.coverages[id].monthly_premium : ratingResult.coverages[id].annual_premium;
  };

  return (
    <div className="rounded-2xl overflow-hidden bg-primary p-[1px]">
      <div className="px-3 py-2.5 text-center font-medium text-white text-sm">
        {needsReview ? 'Under review' : 'Instant quote'}
      </div>
      <div className="bg-surface rounded-t-3xl rounded-b-[calc(1.5rem-1px)] py-3 space-y-3">
        {/* Billing toggle */}
        {!needsReview && showPricing && (
          <div className="px-3">
            <div className="flex gap-1 rounded-xl border border-border-accent bg-bg p-1">
              <button
                type="button"
                onClick={() => onBillingFrequencyChange('monthly')}
                className={`flex-1 rounded-lg border p-2 text-xs font-medium transition-all ${isMonthly ? 'bg-surface border-border-accent text-heading' : 'border-transparent text-muted'}`}
              >
                Monthly
              </button>
              <button
                type="button"
                onClick={() => onBillingFrequencyChange('annual')}
                className={`flex-1 rounded-lg border p-2 text-xs font-medium transition-all ${!isMonthly ? 'bg-surface border-border-accent text-heading' : 'border-transparent text-muted'}`}
              >
                Annual (Save 10%)
              </button>
            </div>
          </div>
        )}

        {/* Price */}
        <div className="px-3">
          <h1 className="font-serif text-[2rem] tracking-tight text-heading">
            {needsReview
              ? 'Waiting for review'
              : showPricing
                ? isMonthly
                  ? `${formatCurrency(totalMonthly)}/month`
                  : `${formatCurrency(totalAnnual)}/year`
                : '$XX/month'}
          </h1>
          <p className="text-sm font-medium text-body">
            {needsReview
              ? `Reference: #${quoteNumber}`
              : effectiveDate
                ? `Effective on ${effectiveDate.toLocaleDateString('en-US', { month: 'numeric', day: 'numeric', year: '2-digit' })}`
                : `Quote #${quoteNumber}`}
          </p>
        </div>

        <div className="h-px bg-border" />

        {/* Coverage breakdown */}
        <div className="px-3 space-y-2">
          {selectedCoverages.map((id) => (
            <div key={id} className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-1.5">
                <span className="text-primary"><CheckIcon size={12} /></span>
                <span className="text-muted text-sm">{AllCoveragesInfo[id]?.name ?? id}</span>
              </div>
              {showPricing && !needsReview && (
                <span className="text-muted text-xs">
                  {formatCurrency(getCoveragePrice(id))}{isMonthly ? '/mo' : '/yr'}
                </span>
              )}
            </div>
          ))}
          {customProducts.map((p) => (
            <div key={p.id} className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-1.5">
                <span className="text-primary"><CheckIcon size={12} /></span>
                <span className="text-muted text-sm">{p.name}</span>
              </div>
              {showPricing && (
                <span className="text-muted text-xs">
                  {formatCurrency(isMonthly ? p.monthly_price : p.price)}{isMonthly ? '/mo' : '/yr'}
                </span>
              )}
            </div>
          ))}
          {hasActivePromo && showPricing && (
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-1.5">
                <span className="text-muted">🏷</span>
                <span className="text-muted text-sm">Partner code</span>
              </div>
              <span className="text-muted text-xs">
                -{formatCurrency(isMonthly ? (discountMonthly ?? 0) : (discountAnnual ?? 0))}{isMonthly ? '/mo' : '/yr'}
              </span>
            </div>
          )}
        </div>

        {/* Total */}
        {!needsReview && showPricing && (
          <>
            <div className="h-px bg-border" />
            <div className="px-3 space-y-1">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-heading">Total</span>
                <span className="font-semibold text-heading">
                  {formatCurrency(isMonthly ? totalMonthly : totalAnnual)}{isMonthly ? '/month' : '/year'}
                </span>
              </div>
              {/* Promo code */}
              {hasActivePromo ? (
                <div className="flex items-center justify-between rounded-lg bg-primary/5 px-3 py-2 mt-2">
                  <span className="font-medium text-primary text-sm">🏷 {promoCode}</span>
                  <button type="button" onClick={onRemovePromoCode} className="text-muted hover:text-heading bg-transparent border-none cursor-pointer">
                    <CloseIcon size={14} />
                  </button>
                </div>
              ) : showPromo ? (
                <div className="flex gap-2 mt-2">
                  <input
                    type="text"
                    value={promoInput}
                    onChange={(e) => setPromoInput(e.target.value)}
                    placeholder="Partner code"
                    className="flex-1 rounded-lg border border-border bg-bg px-3 py-1.5 text-sm outline-none focus:border-primary"
                  />
                  <button
                    type="button"
                    onClick={() => { onApplyPromoCode(promoInput.trim()); setPromoInput(''); }}
                    disabled={!promoInput.trim() || isLoading}
                    className="bg-heading text-white rounded-lg px-3 py-1.5 text-xs font-medium border-none cursor-pointer disabled:opacity-40"
                  >
                    Apply
                  </button>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={() => setShowPromo(true)}
                  className="text-muted text-xs underline underline-offset-2 hover:text-body bg-transparent border-none cursor-pointer p-0"
                >
                  Apply partner code
                </button>
              )}
            </div>
          </>
        )}

        {/* Checkout button */}
        {!needsReview && (
          <>
            <div className="h-px bg-border" />
            <div className="px-3 pb-1">
              <Btn3DOrange
                fullWidth
                disabled={isLoading || !hasAmount || hasUnsavedChanges || !canCheckout}
                onClick={onCheckout}
              >
                {hasAmount && !hasUnsavedChanges && !isLoading && canCheckout
                  ? 'Checkout'
                  : 'Save to Get Quote'
                }
                <ArrowRightIcon />
              </Btn3DOrange>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
