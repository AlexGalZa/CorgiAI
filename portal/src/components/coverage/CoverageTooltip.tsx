'use client';

import { useState, useRef, useCallback, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { getCoverageLabel, getCoverageTooltip } from './constants';

export interface CoverageLabelProps {
  slug: string;
  className?: string;
}

interface TooltipPosition {
  top: number;
  left: number;
  flipped: boolean;
}

function getPosition(trigger: HTMLElement): TooltipPosition {
  const rect = trigger.getBoundingClientRect();
  const TOOLTIP_HEIGHT_ESTIMATE = 60; // rough max height
  const GAP = 8;

  const centerX = rect.left + rect.width / 2;

  // Default: show above the trigger
  let top = rect.top - GAP;
  let flipped = false;

  // If not enough room above, flip below
  if (rect.top < TOOLTIP_HEIGHT_ESTIMATE + GAP) {
    top = rect.bottom + GAP;
    flipped = true;
  }

  return { top, left: centerX, flipped };
}

function TooltipPortal({
  text,
  triggerRef,
}: {
  text: string;
  triggerRef: React.RefObject<HTMLElement | null>;
}) {
  const [pos, setPos] = useState<TooltipPosition | null>(null);

  const update = useCallback(() => {
    if (triggerRef.current) setPos(getPosition(triggerRef.current));
  }, [triggerRef]);

  useEffect(() => {
    update();
    window.addEventListener('scroll', update, true);
    window.addEventListener('resize', update);
    return () => {
      window.removeEventListener('scroll', update, true);
      window.removeEventListener('resize', update);
    };
  }, [update]);

  if (!pos) return null;

  const tooltip = (
    <div
      className="fixed z-[9999] pointer-events-none"
      style={{
        top: pos.top,
        left: pos.left,
        transform: pos.flipped
          ? 'translateX(-50%)'
          : 'translateX(-50%) translateY(-100%)',
      }}
    >
      <div className="relative w-60 rounded-lg bg-heading px-3 py-2 text-xs font-normal text-white leading-[1.4] shadow-lg text-center">
        {text}
        {/* Arrow */}
        {pos.flipped ? (
          /* Arrow pointing up (tooltip is below trigger) */
          <span className="absolute bottom-full left-1/2 -translate-x-1/2 mt-0 border-4 border-transparent border-b-heading" />
        ) : (
          /* Arrow pointing down (tooltip is above trigger) */
          <span className="absolute top-full left-1/2 -translate-x-1/2 -mt-px border-4 border-transparent border-t-heading" />
        )}
      </div>
    </div>
  );

  return createPortal(tooltip, document.body);
}

export function CoverageLabel({ slug, className }: CoverageLabelProps) {
  const label = getCoverageLabel(slug);
  const tooltip = getCoverageTooltip(slug);
  const iconRef = useRef<HTMLElement | null>(null);
  const [hovering, setHovering] = useState(false);

  return (
    <span className={className ?? ''}>
      {label}
      {tooltip && (
        <>
          <span
            ref={iconRef as React.RefObject<HTMLSpanElement>}
            className="inline-flex items-center"
            onMouseEnter={() => setHovering(true)}
            onMouseLeave={() => setHovering(false)}
          >
            <svg
              aria-hidden="true"
              className="inline-block ml-1 w-3.5 h-3.5 text-muted opacity-50 hover:opacity-80 transition-opacity"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <circle cx="12" cy="12" r="10" />
              <path d="M12 16v-4" />
              <path d="M12 8h.01" />
            </svg>
          </span>
          {hovering && <TooltipPortal text={tooltip} triggerRef={iconRef} />}
        </>
      )}
    </span>
  );
}
