'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { HelpCircleIcon } from '@/components/icons';

interface HelpTooltipProps {
  text: string;
  size?: number;
}

/**
 * A help icon (?) that shows a Portal-rendered tooltip on hover.
 * Won't clip inside overflow:hidden containers.
 */
export function HelpTooltip({ text, size = 14 }: HelpTooltipProps) {
  const iconRef = useRef<HTMLSpanElement>(null);
  const [hovering, setHovering] = useState(false);

  return (
    <>
      <span
        ref={iconRef}
        className="relative cursor-help inline-flex items-center justify-center w-3.5 h-3.5 shrink-0 text-muted hover:text-primary transition-colors"
        onMouseEnter={() => setHovering(true)}
        onMouseLeave={() => setHovering(false)}
      >
        <HelpCircleIcon size={size} />
      </span>
      {hovering && iconRef.current && (
        <HelpTooltipPortal text={text} triggerEl={iconRef.current} />
      )}
    </>
  );
}

function HelpTooltipPortal({ text, triggerEl }: { text: string; triggerEl: HTMLElement }) {
  const [pos, setPos] = useState<{ top: number; left: number; flipped: boolean } | null>(null);

  const update = useCallback(() => {
    const rect = triggerEl.getBoundingClientRect();
    const GAP = 8;
    const TOOLTIP_H = 80;
    const centerX = rect.left + rect.width / 2;

    // Prefer below trigger
    if (rect.bottom + GAP + TOOLTIP_H < window.innerHeight) {
      setPos({ top: rect.bottom + GAP, left: centerX, flipped: false });
    } else {
      // Flip above
      setPos({ top: rect.top - GAP, left: centerX, flipped: true });
    }
  }, [triggerEl]);

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

  return createPortal(
    <div
      className="fixed z-[9999] pointer-events-none"
      style={{
        top: pos.top,
        left: pos.left,
        transform: pos.flipped
          ? 'translateX(-50%) translateY(-100%)'
          : 'translateX(-50%)',
      }}
    >
      <div className="relative bg-white text-heading text-xs font-normal font-sans leading-[1.5] p-2 px-3 rounded-xl border border-border whitespace-normal w-60 shadow-[0_4px_12px_rgba(0,0,0,.08)] text-left">
        {text}
        {pos.flipped ? (
          <span className="absolute top-full left-1/2 -translate-x-1/2 -mt-px border-4 border-transparent border-t-white drop-shadow-sm" />
        ) : (
          <span className="absolute bottom-full left-1/2 -translate-x-1/2 mt-px border-4 border-transparent border-b-white drop-shadow-sm" />
        )}
      </div>
    </div>,
    document.body
  );
}
