/**
 * Tests for the RBAC permissions module.
 *
 * Validates that each role gets the correct permissions
 * from the permissions.ts helper functions.
 */

import { describe, it, expect } from 'vitest'
import { permissions } from '@/lib/permissions'

describe('permissions', () => {
  // ── Admin: full access ──────────────────────────────────────────

  describe('admin role', () => {
    const role = 'admin'

    it('has all write permissions', () => {
      expect(permissions.canEditQuotes(role)).toBe(true)
      expect(permissions.canEditPolicies(role)).toBe(true)
      expect(permissions.canEditClaims(role)).toBe(true)
      expect(permissions.canEditOrgs(role)).toBe(true)
      expect(permissions.canEditCertificates(role)).toBe(true)
      expect(permissions.canEditUsers(role)).toBe(true)
    })

    it('has all admin-only permissions', () => {
      expect(permissions.canCreateStaffAccounts(role)).toBe(true)
      expect(permissions.canAssignPermissions(role)).toBe(true)
      expect(permissions.canEditProducers(role)).toBe(true)
      expect(permissions.isAdmin(role)).toBe(true)
    })

    it('has finance permissions', () => {
      expect(permissions.canViewProducers(role)).toBe(true)
      expect(permissions.canViewCommissions(role)).toBe(true)
      expect(permissions.canEditPayments(role)).toBe(true)
    })

    it('has operations permissions', () => {
      expect(permissions.canImpersonateUsers(role)).toBe(true)
      expect(permissions.canDoUnderwriterOverrides(role)).toBe(true)
    })

    it('has read permissions', () => {
      expect(permissions.canViewReports(role)).toBe(true)
      expect(permissions.canExportCSV(role)).toBe(true)
    })
  })

  // ── BDR: limited access ─────────────────────────────────────────

  describe('bdr role', () => {
    const role = 'bdr'

    it('cannot edit quotes', () => {
      expect(permissions.canEditQuotes(role)).toBe(false)
    })

    it('cannot edit policies', () => {
      expect(permissions.canEditPolicies(role)).toBe(false)
    })

    it('cannot edit users', () => {
      expect(permissions.canEditUsers(role)).toBe(false)
    })

    it('can create brokered requests', () => {
      expect(permissions.canCreateBrokeredRequest(role)).toBe(true)
    })

    it('can view reports and export CSV', () => {
      expect(permissions.canViewReports(role)).toBe(true)
      expect(permissions.canExportCSV(role)).toBe(true)
    })

    it('cannot access admin-only features', () => {
      expect(permissions.canCreateStaffAccounts(role)).toBe(false)
      expect(permissions.canAssignPermissions(role)).toBe(false)
      expect(permissions.isAdmin(role)).toBe(false)
    })

    it('is identified as BDR', () => {
      expect(permissions.isBDR(role)).toBe(true)
    })
  })

  // ── Finance: read + finance-specific ────────────────────────────

  describe('finance role', () => {
    const role = 'finance'

    it('cannot edit quotes or policies', () => {
      expect(permissions.canEditQuotes(role)).toBe(false)
      expect(permissions.canEditPolicies(role)).toBe(false)
    })

    it('can view and edit payments', () => {
      expect(permissions.canEditPayments(role)).toBe(true)
      expect(permissions.canViewCommissions(role)).toBe(true)
      expect(permissions.canViewProducers(role)).toBe(true)
    })

    it('cannot impersonate users', () => {
      expect(permissions.canImpersonateUsers(role)).toBe(false)
    })

    it('is identified as finance', () => {
      expect(permissions.isFinance(role)).toBe(true)
    })
  })

  // ── Broker: restricted view ─────────────────────────────────────

  describe('broker role', () => {
    const role = 'broker'

    it('cannot edit quotes', () => {
      expect(permissions.canEditQuotes(role)).toBe(false)
    })

    it('cannot view users or create staff accounts', () => {
      expect(permissions.canEditUsers(role)).toBe(false)
      expect(permissions.canCreateStaffAccounts(role)).toBe(false)
    })

    it('cannot view producers or commissions', () => {
      expect(permissions.canViewProducers(role)).toBe(false)
      expect(permissions.canViewCommissions(role)).toBe(false)
    })

    it('can view reports', () => {
      expect(permissions.canViewReports(role)).toBe(true)
    })

    it('is identified as broker', () => {
      expect(permissions.isBroker(role)).toBe(true)
    })
  })

  // ── AE: write access ───────────────────────────────────────────

  describe('ae role', () => {
    const role = 'ae'

    it('can edit quotes and policies', () => {
      expect(permissions.canEditQuotes(role)).toBe(true)
      expect(permissions.canEditPolicies(role)).toBe(true)
    })

    it('can impersonate users', () => {
      expect(permissions.canImpersonateUsers(role)).toBe(true)
    })

    it('cannot do underwriter overrides', () => {
      expect(permissions.canDoUnderwriterOverrides(role)).toBe(false)
    })

    it('cannot create staff accounts', () => {
      expect(permissions.canCreateStaffAccounts(role)).toBe(false)
    })
  })

  // ── AE + Underwriting: write + underwriting ─────────────────────

  describe('ae_underwriting role', () => {
    const role = 'ae_underwriting'

    it('can edit quotes and policies', () => {
      expect(permissions.canEditQuotes(role)).toBe(true)
      expect(permissions.canEditPolicies(role)).toBe(true)
    })

    it('can do underwriter overrides', () => {
      expect(permissions.canDoUnderwriterOverrides(role)).toBe(true)
    })

    it('can impersonate users', () => {
      expect(permissions.canImpersonateUsers(role)).toBe(true)
    })
  })

  // ── Policyholder (not a staff role) ─────────────────────────────

  describe('policyholder role (non-staff)', () => {
    const role = 'policyholder'

    it('has no staff permissions', () => {
      expect(permissions.canEditQuotes(role)).toBe(false)
      expect(permissions.canEditPolicies(role)).toBe(false)
      expect(permissions.canViewReports(role)).toBe(false)
      expect(permissions.canExportCSV(role)).toBe(false)
      expect(permissions.isAdmin(role)).toBe(false)
    })
  })
})
