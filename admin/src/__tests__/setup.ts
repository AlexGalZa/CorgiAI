/**
 * Test setup for the Corgi admin panel.
 *
 * Configures Vitest with any global mocks or setup needed.
 * This file is referenced in vitest.config.ts as setupFiles.
 */

// Mock zustand stores to avoid React context issues in unit tests
import { vi } from 'vitest'

// Mock the auth store used by usePermissions
vi.mock('@/stores/auth', () => ({
  useAuthStore: vi.fn((selector) => {
    // Default: return undefined user (tests override as needed)
    const state = { user: null }
    return selector ? selector(state) : state
  }),
}))
