/**
 * Canonical admin role constants.
 *
 * These mirror the backend groupings in `api/admin_api/helpers.py` so the
 * frontend role-guard and the Django RBAC checks stay in lockstep. Import
 * from this module instead of redefining role lists at call sites.
 */

import type { Role } from './permissions'

export const ADMIN_ROLES: Role[] = ['admin']
export const FINANCE_ROLES: Role[] = ['finance', 'admin']
export const STAFF_ROLES: Role[] = ['ae', 'ae_underwriting', 'admin']
export const UNDERWRITING_ROLES: Role[] = ['ae_underwriting', 'admin']
export const CLAIMS_ROLES: Role[] = ['claims_adjuster', 'ae', 'ae_underwriting', 'admin']
export const SUPPORT_ROLES: Role[] = ['customer_support', 'ae', 'ae_underwriting', 'admin']
export const ALL_INTERNAL_ROLES: Role[] = ['bdr', 'ae', 'ae_underwriting', 'finance', 'admin']
