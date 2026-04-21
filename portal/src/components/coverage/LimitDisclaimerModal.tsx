'use client';

import { useState } from 'react';
import { Modal } from '@/components/ui/modal';
import { Btn3DWhite, Btn3DOrange } from '@/components/ui/button';
import { CloseIcon, InfoIcon, CheckIcon, ShieldIcon } from '@/components/icons';

export interface LimitDisclaimerModalProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
}

export function LimitDisclaimerModal({
  open,
  onClose,
  onConfirm,
}: LimitDisclaimerModalProps) {
  const [checks, setChecks] = useState([false, false, false]);
  const [signature, setSignature] = useState('');
  const allChecked = checks.every(Boolean);
  const canConfirm = allChecked && signature.trim().length >= 2;

  const toggle = (idx: number) => {
    setChecks((prev) => prev.map((v, i) => (i === idx ? !v : v)));
  };

  const declarations = [
    {
      label: 'No known incidents',
      desc: 'I confirm that no incidents, events, or circumstances that could give rise to a claim have occurred since the policy inception or last renewal date.',
    },
    {
      label: 'No pending or filed claims',
      desc: 'I confirm that no claims have been filed, and no notice of any potential claim has been given to us or any other insurer.',
    },
    {
      label: 'No material changes',
      desc: 'I confirm that there have been no material changes to the business operations, financial condition, or risk profile since the policy was issued.',
    },
  ];

  return (
    <Modal open={open} onClose={onClose} width={520} titleId="disclaimer-title">
      {/* Header */}
      <div className="px-6 pt-6 flex flex-col gap-4">
        <div className="flex items-start justify-between">
          <div className="flex flex-col gap-2">
            <div id="disclaimer-title" className="font-heading text-2xl font-normal text-heading tracking-[-0.768px] leading-none">
              Before you continue
            </div>
            <div className="text-sm font-normal text-body leading-[1.2]">
              Please confirm the following declarations before adjusting your coverage limits.
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close"
            className="bg-transparent border-none cursor-pointer p-0 leading-none shrink-0"
          >
            <CloseIcon size={24} color="var(--color-heading)" />
          </button>
        </div>
      </div>

      {/* Declarations */}
      <div className="p-5 px-6 flex flex-col gap-4">
        <div className="flex flex-col gap-0">
          {declarations.map((d, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => toggle(idx)}
              className="flex items-start gap-3 p-3 cursor-pointer bg-transparent border-none text-left w-full"
            >
              <div
                className={`w-5 h-5 rounded-lg border flex items-center justify-center shrink-0 mt-0.5 transition-colors ${
                  checks[idx]
                    ? 'bg-primary border-primary'
                    : 'bg-white border-border'
                }`}
              >
                {checks[idx] && <CheckIcon size={10} color="currentColor" strokeWidth={3} />}
              </div>
              <div className="flex flex-col gap-1">
                <div className="text-sm font-semibold text-heading leading-[1.2]">{d.label}</div>
                <div className="text-xs font-normal text-muted leading-[1.4]">{d.desc}</div>
              </div>
            </button>
          ))}
        </div>

        {/* Signature field */}
        <div className="flex flex-col gap-1">
          <label className="text-[11px] font-semibold text-heading leading-[1.2]">
            Type your full name as signature
          </label>
          <input
            type="text"
            value={signature}
            onChange={(e) => setSignature(e.target.value)}
            placeholder="Full legal name"
            className="w-full bg-white border border-border rounded-lg px-3 py-2.5 text-sm text-heading font-sans placeholder:text-muted"
          />
        </div>

        {/* Warning box */}
        <div className="p-3 flex items-start gap-2 bg-[rgba(255,222,204,0.2)] border border-primary/50 rounded-xl">
          <InfoIcon size={16} color="var(--color-primary)" />
          <span className="text-[11px] font-normal text-body leading-[1.4]">
            By proceeding, you acknowledge that these declarations are true and accurate. Providing
            false information may void your coverage or result in denial of future claims.
          </span>
        </div>

        {/* Buttons */}
        <div className="flex gap-3">
          <Btn3DWhite fullWidth onClick={onClose}>
            Cancel
          </Btn3DWhite>
          <Btn3DOrange
            fullWidth
            onClick={() => {
              onClose();
              onConfirm();
            }}
            disabled={!canConfirm}
            className={!canConfirm ? 'opacity-40 pointer-events-none' : ''}
          >
            <ShieldIcon className="w-4 h-4 stroke-white shrink-0" /> Confirm &amp; continue
          </Btn3DOrange>
        </div>
      </div>
    </Modal>
  );
}
