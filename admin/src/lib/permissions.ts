export type Role =
  | 'bdr'
  | 'ae'
  | 'ae_underwriting'
  | 'finance'
  | 'broker'
  | 'admin'
  | 'claims_adjuster'
  | 'customer_support'

// Role groupings matching the permission matrix.
// These remain for backward-compat with existing call sites and tests.
const WRITE_ROLES: Role[] = ['ae', 'ae_underwriting', 'admin']
const READ_ROLES: Role[] = ['bdr', 'ae', 'ae_underwriting', 'finance', 'broker', 'admin']
const ADMIN_ONLY: Role[] = ['admin']
const FINANCE_OR_ADMIN: Role[] = ['finance', 'admin']
const UNDERWRITING_ROLES: Role[] = ['ae_underwriting', 'admin']
const OPERATIONS_ROLES: Role[] = ['ae', 'ae_underwriting', 'admin']

export const permissions = {
  canEditQuotes: (role: string) => WRITE_ROLES.includes(role as Role),
  canEditPolicies: (role: string) => WRITE_ROLES.includes(role as Role),
  canEditClaims: (role: string) => WRITE_ROLES.includes(role as Role),
  canEditOrgs: (role: string) => WRITE_ROLES.includes(role as Role),
  canEditCertificates: (role: string) => UNDERWRITING_ROLES.includes(role as Role),
  canEditUsers: (role: string) => WRITE_ROLES.includes(role as Role),
  canCreateBrokeredRequest: (role: string) => [...WRITE_ROLES, 'bdr'].includes(role as Role),
  canEditBrokeredRequest: (role: string) => WRITE_ROLES.includes(role as Role),
  canDoUnderwriterOverrides: (role: string) => UNDERWRITING_ROLES.includes(role as Role),
  canViewProducers: (role: string) => FINANCE_OR_ADMIN.includes(role as Role),
  canEditProducers: (role: string) => ADMIN_ONLY.includes(role as Role),
  canViewCommissions: (role: string) => FINANCE_OR_ADMIN.includes(role as Role),
  canCreateStaffAccounts: (role: string) => ADMIN_ONLY.includes(role as Role),
  canAssignPermissions: (role: string) => ADMIN_ONLY.includes(role as Role),
  canImpersonateUsers: (role: string) => OPERATIONS_ROLES.includes(role as Role),
  canViewReports: (role: string) => READ_ROLES.includes(role as Role),
  canExportCSV: (role: string) => READ_ROLES.includes(role as Role),
  canEditPayments: (role: string) => FINANCE_OR_ADMIN.includes(role as Role),
  isAdmin: (role: string) => ADMIN_ONLY.includes(role as Role),
  isBroker: (role: string) => role === 'broker',
  isBDR: (role: string) => role === 'bdr',
  isFinance: (role: string) => role === 'finance',
}

// SSO permission keys used as the source of truth for runtime authorization.
// admin.manage: full write access (equivalent to the old WRITE_ROLES + ADMIN_ONLY bucket).
// admin.view: read access (equivalent to the old READ_ROLES bucket).
const PERM_MANAGE = 'admin.manage'
const PERM_VIEW = 'admin.view'

// Hook for convenience.
// Reads sso permission keys from user.permissions instead of user.role.
import { useAuthStore } from '@/stores/auth'

export function usePermissions() {
  // Return the raw permissions reference (or undefined). A `?? []` in the
  // selector produces a fresh array on every call, which Zustand compares by
  // reference and treats as a change, causing an infinite re-render.
  const userPermissions = useAuthStore((s) => s.user?.permissions)
  const role = useAuthStore((s) => s.user?.role ?? '')

  const hasManage = userPermissions?.includes(PERM_MANAGE) ?? false
  const hasView = userPermissions?.includes(PERM_VIEW) ?? false

  return {
    role,
    // Write gates: require admin.manage
    canEditQuotes: hasManage,
    canEditPolicies: hasManage,
    canEditClaims: hasManage,
    canEditOrgs: hasManage,
    canEditCertificates: hasManage,
    canEditUsers: hasManage,
    canCreateBrokeredRequest: hasManage,
    canEditBrokeredRequest: hasManage,
    canDoUnderwriterOverrides: hasManage,
    canViewProducers: hasManage,
    canEditProducers: hasManage,
    canViewCommissions: hasManage,
    canCreateStaffAccounts: hasManage,
    canAssignPermissions: hasManage,
    canImpersonateUsers: hasManage,
    canEditPayments: hasManage,
    isAdmin: hasManage,
    // Read gates: require admin.view (admin.manage also implies view access)
    canViewReports: hasView || hasManage,
    canExportCSV: hasView || hasManage,
    // Identity flags: fall back to role string for non-SSO sessions
    isBroker: role === 'broker',
    isBDR: role === 'bdr',
    isFinance: role === 'finance',
  } as Record<keyof typeof permissions, boolean> & { role: string }
}
