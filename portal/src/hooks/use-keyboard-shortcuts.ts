import { useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';

const G_COMBOS: Record<string, string> = {
  c: '/',           // g+c → coverage
  b: '/billing',    // g+b → billing
  d: '/documents',  // g+d → documents
  l: '/claims',     // g+l → claims (l for "loss")
  q: '/quotes',     // g+q → quotes
  o: '/organization', // g+o → organization
  e: '/certificates', // g+e → certificates (e for "evidence")
};

export function useKeyboardShortcuts() {
  const router = useRouter();
  const gPressedAt = useRef<number>(0);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement).tagName;
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes(tag)) return;

      // Cmd/Ctrl+K → focus search
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        document.querySelector<HTMLInputElement>('[data-search-input]')?.focus();
        return;
      }

      // "g" prefix for navigation combos
      if (e.key === 'g' && !e.metaKey && !e.ctrlKey && !e.altKey) {
        gPressedAt.current = Date.now();
        return;
      }

      // Check g+key combo (within 500ms)
      if (Date.now() - gPressedAt.current < 500) {
        const dest = G_COMBOS[e.key];
        if (dest) {
          e.preventDefault();
          router.push(dest);
          gPressedAt.current = 0;
          return;
        }
      }
    };

    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [router]);
}
