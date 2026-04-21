import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

export interface Organization {
  id: number;
  name: string;
  role: string;
  is_personal: boolean;
}

interface OrgState {
  activeOrgId: number | null;
  organizations: Organization[];
  setActiveOrgId: (orgId: number) => void;
  setOrganizations: (orgs: Organization[]) => void;
  clearActiveOrg: () => void;
}

export const useOrgStore = create<OrgState>()(
  persist(
    (set) => ({
      activeOrgId: null,
      organizations: [],
      setActiveOrgId: (orgId) => set({ activeOrgId: orgId }),
      setOrganizations: (orgs) => set({ organizations: orgs }),
      clearActiveOrg: () => set({ activeOrgId: null, organizations: [] }),
    }),
    {
      name: 'corgi-org',
      storage: createJSONStorage(() => localStorage),
    }
  )
);
