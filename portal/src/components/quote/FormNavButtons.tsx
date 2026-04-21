'use client';

import { Btn3DDark, Btn3DOrange } from '@/components/ui/button';
import { ArrowLeftIcon, ArrowRightIcon } from '@/components/icons';

interface Props {
  onBack?: () => void;
  onNext?: () => void;
  nextLabel?: string;
  nextType?: 'button' | 'submit';
  loading?: boolean;
  disableNext?: boolean;
  showBack?: boolean;
}

export function FormNavButtons({
  onBack,
  onNext,
  nextLabel = 'Next',
  nextType = 'submit',
  loading = false,
  disableNext = false,
  showBack = true,
}: Props) {
  return (
    <div className="flex items-center justify-between mt-8">
      {showBack && onBack ? (
        <Btn3DDark onClick={onBack} type="button">
          <ArrowLeftIcon /> Back
        </Btn3DDark>
      ) : (
        <div />
      )}
      <Btn3DOrange
        onClick={nextType === 'button' ? onNext : undefined}
        type={nextType}
        disabled={loading || disableNext}
      >
        {loading ? 'Saving...' : nextLabel} <ArrowRightIcon />
      </Btn3DOrange>
    </div>
  );
}
