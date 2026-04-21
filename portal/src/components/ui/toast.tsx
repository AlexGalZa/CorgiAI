'use client';

import { useAppStore } from '@/stores/use-app-store';
import { CloseIcon } from '@/components/icons';

const VARIANT_STYLES: Record<string, string> = {
  success: 'bg-success',
  error: 'bg-danger',
  info: 'bg-primary',
  default: 'bg-heading',
};

export default function Toast() {
  const { toasts, dismissToast } = useAppStore();

  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-[9999] flex flex-col-reverse gap-2 items-center pointer-events-none">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`pointer-events-auto flex items-center gap-2 px-5 py-2.5 rounded-lg text-[13px] font-sans font-bold text-white shadow-lg transition-all duration-200 animate-enter ${VARIANT_STYLES[toast.variant] || VARIANT_STYLES.default}`}
        >
          <span>{toast.message}</span>
          <button
            onClick={() => dismissToast(toast.id)}
            className="bg-transparent border-none cursor-pointer p-0 ml-1 flex items-center opacity-70 hover:opacity-100 transition-opacity"
            aria-label="Dismiss"
          >
            <CloseIcon size={14} color="white" />
          </button>
        </div>
      ))}
    </div>
  );
}
