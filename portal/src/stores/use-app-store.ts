import { create } from 'zustand';
import type { TabName } from '@/types';

export type ToastVariant = 'default' | 'success' | 'error' | 'info';

interface ToastItem {
  id: number;
  message: string;
  variant: ToastVariant;
}

// Legacy shape for backwards compat
interface LegacyToast {
  message: string;
  visible: boolean;
}

interface AppState {
  activeTab: TabName;
  toast: LegacyToast;
  toasts: ToastItem[];
  accountPopupOpen: boolean;
  sidebarOpen: boolean;
  mobileSidebarOpen: boolean;
  switchTab: (tab: TabName) => void;
  showToast: (message: string, variant?: ToastVariant) => void;
  dismissToast: (id: number) => void;
  hideToast: () => void;
  setAccountPopupOpen: (open: boolean) => void;
  toggleAccountPopup: () => void;
  setSidebarOpen: (open: boolean) => void;
  setMobileSidebarOpen: (open: boolean) => void;
  toggleMobileSidebar: () => void;
}

let nextToastId = 0;

export const useAppStore = create<AppState>((set) => ({
  activeTab: 'coverage',
  toast: { message: '', visible: false },
  toasts: [],
  accountPopupOpen: false,
  sidebarOpen: true,
  mobileSidebarOpen: false,
  switchTab: (tab) => set({ activeTab: tab }),
  showToast: (message, variant = 'default') => {
    const id = ++nextToastId;
    set((state) => ({
      toast: { message, visible: true },
      toasts: [...state.toasts, { id, message, variant }],
    }));
    // Auto-dismiss after 3 seconds
    setTimeout(() => {
      set((state) => ({
        toasts: state.toasts.filter((t) => t.id !== id),
        toast: state.toasts.length <= 1 ? { message: '', visible: false } : state.toast,
      }));
    }, 3000);
  },
  dismissToast: (id) => {
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
      toast: state.toasts.length <= 1 ? { message: '', visible: false } : state.toast,
    }));
  },
  hideToast: () => set({ toast: { message: '', visible: false }, toasts: [] }),
  setAccountPopupOpen: (open) => set({ accountPopupOpen: open }),
  toggleAccountPopup: () =>
    set((s) => ({ accountPopupOpen: !s.accountPopupOpen })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  setMobileSidebarOpen: (open) => set({ mobileSidebarOpen: open }),
  toggleMobileSidebar: () => set((s) => ({ mobileSidebarOpen: !s.mobileSidebarOpen })),
}));
