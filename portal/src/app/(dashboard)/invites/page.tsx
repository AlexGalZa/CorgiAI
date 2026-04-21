'use client';

import Link from 'next/link';
import { usePageTitle } from '@/hooks/use-page-title';
import { BtnSecondary } from '@/components/ui/button';

/**
 * Invitations inbox page.
 *
 * A user-facing "pending invites for me" endpoint does not exist in the
 * current API. The existing /api/v1/organizations/invites endpoints are
 * owner-managed outbound invite links, not inbox invitations addressed to
 * the current user. This page renders a friendly empty state until a
 * suitable endpoint is added.
 */
export default function InvitesPage() {
  usePageTitle('Invitations');

  return (
    <div className="max-w-[1100px] mx-auto px-4 sm:px-6 md:px-12 py-6 md:py-10 flex flex-col gap-8">
      {/* Page header */}
      <div className="flex flex-col gap-1">
        <span className="text-[11px] font-semibold text-muted tracking-normal leading-[1.2] uppercase">
          Account
        </span>
        <h1 className="font-heading text-[26px] sm:text-[32px] font-medium text-heading tracking-[-1.024px] leading-none">
          Invitations
        </h1>
      </div>

      {/* Empty state */}
      <div className="border border-dashed border-border rounded-2xl text-center py-16 px-10 flex flex-col items-center gap-4">
        <div className="w-12 h-12 rounded-full bg-border flex items-center justify-center text-muted">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
            <polyline points="22,6 12,13 2,6"/>
          </svg>
        </div>
        <div className="flex flex-col gap-1">
          <div className="text-sm font-medium text-heading">No pending invitations</div>
          <div className="text-[13px] text-muted leading-[1.5] max-w-sm">
            When someone invites you to join an organization, it will appear here.
          </div>
        </div>
        <Link href="/">
          <BtnSecondary>Back to coverage</BtnSecondary>
        </Link>
      </div>
    </div>
  );
}
