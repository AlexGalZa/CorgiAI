'use client';

import { useEffect, useRef, useCallback, type ReactNode, type MouseEvent } from 'react';

interface ModalProps {
  open: boolean;
  onClose: () => void;
  width?: number;
  children: ReactNode;
  /** Optional id for aria-labelledby. Defaults to "modal-title". */
  titleId?: string;
}

export function Modal({ open, onClose, width = 520, children, titleId = 'modal-title' }: ModalProps) {
  const overlayRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  const handleOverlay = (e: MouseEvent) => {
    if (e.target === e.currentTarget) onClose();
  };

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [open, onClose]);

  // Focus trap: focus first focusable element on open, restore on close
  useEffect(() => {
    if (open) {
      previousFocusRef.current = document.activeElement as HTMLElement;
      // Delay to allow animation/render
      requestAnimationFrame(() => {
        if (contentRef.current) {
          const focusable = contentRef.current.querySelector<HTMLElement>(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
          );
          focusable?.focus();
        }
      });
    } else {
      // Restore focus to trigger element
      previousFocusRef.current?.focus();
      previousFocusRef.current = null;
    }
  }, [open]);

  // Trap tab inside modal
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key !== 'Tab' || !contentRef.current) return;
    const focusableEls = contentRef.current.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    if (focusableEls.length === 0) return;
    const first = focusableEls[0];
    const last = focusableEls[focusableEls.length - 1];
    if (e.shiftKey) {
      if (document.activeElement === first) {
        e.preventDefault();
        last.focus();
      }
    } else {
      if (document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
  }, []);

  return (
    <div
      ref={overlayRef}
      className={`fixed inset-0 bg-black/40 flex items-end md:items-center justify-center z-[100] transition-opacity duration-200 ${open ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'}`}
      onClick={handleOverlay}
      aria-hidden={!open}
    >
      <div
        ref={contentRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onKeyDown={handleKeyDown}
        className={`w-full md:w-auto max-h-[95vh] md:max-h-[90vh] overflow-auto bg-[var(--color-card-bg)] border border-[var(--color-border-raw)] rounded-t-2xl md:rounded-2xl shadow-[0_24px_48px_-12px_rgba(0,0,0,.18)] dark:shadow-[0_24px_48px_-12px_rgba(0,0,0,.5)] ${open ? 'animate-enter' : ''}`}
        style={{ maxWidth: '100%', ...(width ? { width: `min(${width}px, 100%)` } : {}) }}
      >
        {children}
      </div>
    </div>
  );
}
