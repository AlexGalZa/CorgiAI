'use client';

import { useState, useCallback } from 'react';
import { usePageTitle } from '@/hooks/use-page-title';
import {
  useOrganization,
  useUpdateOrganization,
  useCreateInvite,
  useRevokeInvite,
  useRemoveMember,
  useUpdateMemberRole,
  useLeaveOrganization,
} from '@/hooks/use-organization';
import { useAppStore } from '@/stores/use-app-store';
import { Btn3DWhite, Btn3DOrange, BtnDanger, BtnDangerConfirm } from '@/components/ui/button';
import { Input, Label } from '@/components/ui/input';
import { CustomSelect } from '@/components/ui/custom-select';
import { Modal } from '@/components/ui/modal';
import { PlusIcon, CloseIcon, UserIcon, AlertCircleIcon } from '@/components/icons';

const ROLE_COLORS: Record<string, string> = {
  owner: 'var(--color-muted)',
  editor: 'var(--color-muted)',
  viewer: 'var(--color-muted)',
};

function getInitials(firstName: string, lastName: string): string {
  return `${firstName.charAt(0)}${lastName.charAt(0)}`.toUpperCase();
}

function getRoleColor(role: string): string {
  return ROLE_COLORS[role.toLowerCase()] ?? 'var(--color-muted)';
}

function LoadingSkeleton() {
  return (
    <div className="max-w-[1100px] mx-auto px-4 sm:px-6 md:px-12 py-6 md:py-10 flex flex-col gap-8 animate-pulse">
      <div className="flex items-end justify-between">
        <div className="flex flex-col gap-2">
          <div className="h-3 w-24 bg-border rounded" />
          <div className="h-8 w-56 bg-border rounded" />
        </div>
      </div>
      <div className="flex gap-8">
        <div className="flex-1 flex flex-col gap-6">
          <div className="h-48 bg-border rounded-2xl" />
          <div className="h-24 bg-border rounded-2xl" />
        </div>
        <div className="flex-1 flex flex-col gap-6">
          <div className="h-36 bg-border rounded-2xl" />
          <div className="h-24 bg-border rounded-2xl" />
        </div>
      </div>
    </div>
  );
}

export default function OrganizationPage() {
  usePageTitle('Organization');
  const { data: org, isLoading, isError, refetch } = useOrganization();
  const updateOrgMutation = useUpdateOrganization();
  const createInviteMutation = useCreateInvite();
  const revokeInviteMutation = useRevokeInvite();
  const removeMemberMutation = useRemoveMember();
  const updateMemberRoleMutation = useUpdateMemberRole();
  const leaveOrgMutation = useLeaveOrganization();
  const { showToast } = useAppStore();

  const [editOrgOpen, setEditOrgOpen] = useState(false);
  const [removeOrgOpen, setRemoveOrgOpen] = useState(false);
  const [inviteMemberOpen, setInviteMemberOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState<'viewer' | 'editor' | 'owner'>('viewer');
  const [orgName, setOrgName] = useState('');
  const [orgPhone, setOrgPhone] = useState('');
  const [orgEmail, setOrgEmail] = useState('');
  const [orgWebsite, setOrgWebsite] = useState('');

  // Open edit modal pre-filled
  const openEditModal = useCallback(() => {
    setOrgName(org?.name ?? '');
    setOrgPhone((org as any)?.phone ?? '');
    setOrgEmail((org as any)?.billing_email ?? '');
    setOrgWebsite((org as any)?.website ?? '');
    setEditOrgOpen(true);
  }, [org]);

  const handleSaveOrg = useCallback(() => {
    updateOrgMutation.mutate(
      { name: orgName, phone: orgPhone, billing_email: orgEmail, website: orgWebsite },
      {
        onSuccess: () => {
          setEditOrgOpen(false);
          showToast('Organization updated', 'success');
        },
        onError: (error) => {
          showToast(`Error: ${error.message}`, 'error');
        },
      }
    );
  }, [updateOrgMutation, orgName, orgPhone, orgEmail, orgWebsite, showToast]);

  const createInvite = useCallback(() => {
    createInviteMutation.mutate(
      { default_role: 'viewer' },
      {
        onSuccess: (invite) => {
          showToast('Invite link created: ' + invite.code);
        },
        onError: (error) => {
          showToast(`Error: ${error.message}`);
        },
      }
    );
  }, [createInviteMutation, showToast]);

  const handleInviteMember = useCallback(() => {
    if (!inviteEmail.trim()) return;
    createInviteMutation.mutate(
      { default_role: inviteRole, email: inviteEmail.trim(), max_uses: 1 },
      {
        onSuccess: () => {
          setInviteMemberOpen(false);
          setInviteEmail('');
          setInviteRole('viewer');
          showToast('Invite sent to ' + inviteEmail.trim(), 'success');
        },
        onError: (error) => {
          showToast(`Error: ${error.message}`, 'error');
        },
      }
    );
  }, [createInviteMutation, inviteEmail, inviteRole, showToast]);

  const handleRemoveMember = useCallback(
    (userId: number, name: string) => {
      if (!window.confirm(`Remove ${name} from the organization?`)) return;
      removeMemberMutation.mutate(userId, {
        onSuccess: () => showToast('Member removed', 'success'),
        onError: (error) => showToast(`Error: ${error.message}`, 'error'),
      });
    },
    [removeMemberMutation, showToast]
  );

  const handleRoleChange = useCallback(
    (userId: number, role: string) => {
      updateMemberRoleMutation.mutate(
        { userId, role },
        {
          onSuccess: () => showToast('Role updated', 'success'),
          onError: (error) => showToast(`Error: ${error.message}`, 'error'),
        }
      );
    },
    [updateMemberRoleMutation, showToast]
  );

  const removeInvite = useCallback(
    (inviteId: number) => {
      revokeInviteMutation.mutate(inviteId, {
        onSuccess: () => showToast('Invite link revoked'),
        onError: (error) => showToast(`Error: ${error.message}`),
      });
    },
    [revokeInviteMutation, showToast]
  );

  const copyInvite = useCallback(
    (code: string) => {
      navigator.clipboard
        .writeText(code)
        .then(() => showToast('Copied ' + code + ' to clipboard'));
    },
    [showToast]
  );

  const handleRemoveOrg = useCallback(() => {
    leaveOrgMutation.mutate(undefined, {
      onSuccess: () => {
        setRemoveOrgOpen(false);
        showToast('Left organization');
      },
      onError: (error) => {
        showToast(`Error: ${error.message}`);
      },
    });
  }, [leaveOrgMutation, showToast]);

  if (isLoading) return <LoadingSkeleton />;

  if (isError) {
    return (
      <div className="max-w-[1100px] mx-auto px-4 sm:px-6 md:px-12 py-6 md:py-10 flex flex-col items-center gap-4 pt-32">
        <div className="text-sm text-muted">Failed to load organization.</div>
        <button
          onClick={() => refetch()}
          className="text-sm font-medium text-primary bg-transparent border border-primary rounded-xl px-4 py-2 cursor-pointer hover:bg-primary hover:text-white transition-colors focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none"
        >
          Retry
        </button>
      </div>
    );
  }

  const members = org?.members ?? [];
  const allInvites = org?.invites ?? [];
  const invites = allInvites.filter((inv) => inv.is_valid);
  const pendingInvites = invites; // All valid invites are pending

  return (
    <div className="max-w-[1100px] mx-auto px-4 sm:px-6 md:px-12 py-6 md:py-10 flex flex-col gap-8">
      {/* Page header */}
      <div className="flex items-end justify-between">
        <div className="flex flex-col gap-1">
          <span className="text-[11px] font-semibold text-muted tracking-normal leading-[1.2] uppercase">Organization</span>
          <h1 className="font-heading text-[26px] sm:text-[32px] font-medium text-heading tracking-[-1.024px] leading-none">Manage Your Team.</h1>
        </div>
      </div>

      {/* Two-column layout */}
      <div className="flex gap-8 items-start">
        {/* Left column */}
        <div className="flex-1 flex flex-col gap-6">
          {/* Org Details */}
          <div className="bg-surface border border-border rounded-2xl overflow-hidden">
            <div className="flex items-center justify-between px-6 py-5">
              <span className="font-heading text-2xl font-normal text-heading tracking-[-0.768px] leading-none">
                {org?.name ?? 'Organization'}
              </span>
              <Btn3DWhite onClick={openEditModal}>
                <span className="text-xs font-normal">Edit</span>
              </Btn3DWhite>
            </div>
            <div className="px-6 pb-5 flex flex-col gap-6">
              <div className="flex flex-col gap-1">
                <span className="text-[11px] font-normal text-muted leading-[1.2]">Organization name</span>
                <span className="text-sm font-medium text-heading leading-[1.2]">{org?.name}</span>
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-[11px] font-normal text-muted leading-[1.2]">Your role</span>
                <span className="text-sm font-medium text-heading leading-[1.2] capitalize">{org?.role}</span>
              </div>
              {(org as any)?.billing_email && (
                <div className="flex flex-col gap-1">
                  <span className="text-[11px] font-normal text-muted leading-[1.2]">Contact email</span>
                  <span className="text-sm font-medium text-heading leading-[1.2]">{(org as any).billing_email}</span>
                </div>
              )}
              {(org as any)?.phone && (
                <div className="flex flex-col gap-1">
                  <span className="text-[11px] font-normal text-muted leading-[1.2]">Phone</span>
                  <span className="text-sm font-medium text-heading leading-[1.2]">{(org as any).phone}</span>
                </div>
              )}
              <div className="flex flex-col gap-1">
                <span className="text-[11px] font-normal text-muted leading-[1.2]">Members</span>
                <span className="text-sm font-medium text-heading leading-[1.2]">{members.length}</span>
              </div>
            </div>
          </div>

          {/* Members */}
          <div className="bg-surface border border-border rounded-2xl overflow-hidden">
            <div className="flex items-center justify-between px-6 py-5">
              <span className="font-heading text-2xl font-normal text-heading tracking-[-0.768px] leading-none">Members</span>
              {org?.role === 'owner' && (
                <Btn3DOrange onClick={() => { setInviteEmail(''); setInviteRole('viewer'); setInviteMemberOpen(true); }}>
                  <PlusIcon size={16} color="white" /> Invite Member
                </Btn3DOrange>
              )}
            </div>
            <div className="px-6 pb-5 flex flex-col gap-4">
              {members.map((member) => (
                <div key={member.id} className="flex items-center justify-between group">
                  <div className="flex items-center gap-2">
                    <div
                      className="w-8 h-8 rounded-full flex items-center justify-center shrink-0"
                      style={{ backgroundColor: getRoleColor(member.role) }}
                    >
                      <span className="text-[11px] font-medium text-white font-sans leading-none">
                        {getInitials(member.first_name, member.last_name)}
                      </span>
                    </div>
                    <div className="flex flex-col gap-1">
                      <span className="text-sm leading-[1.2] text-heading">
                        <span className="font-medium">
                          {member.first_name} {member.last_name}
                        </span>
                      </span>
                      <span className="text-[11px] font-normal text-heading leading-[1.2]">{member.email}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {org?.role === 'owner' && member.role !== 'owner' ? (
                      <>
                        <CustomSelect
                          value={member.role}
                          onChange={(val) => handleRoleChange(member.id, val)}
                          options={[
                            { value: 'viewer', label: 'Viewer' },
                            { value: 'editor', label: 'Editor' },
                          ]}
                          className="!w-auto !py-1 !px-2 !text-[10px] !rounded-full !bg-bg"
                        />
                        <button
                          onClick={() => handleRemoveMember(member.id, `${member.first_name} ${member.last_name}`)}
                          className="opacity-0 group-hover:opacity-100 bg-transparent border-none cursor-pointer p-0 flex items-center justify-center shrink-0 transition-opacity"
                        >
                          <CloseIcon size={14} color="var(--color-muted)" />
                        </button>
                      </>
                    ) : (
                      <span className="text-[10px] font-medium text-body bg-bg border border-border rounded-full py-1 px-2 leading-none font-sans capitalize">
                        {member.role}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right column */}
        <div className="flex-1 flex flex-col gap-6">
          {/* Invite Links */}
          <div className="bg-surface border border-border rounded-2xl overflow-hidden">
            <div className="flex items-center justify-between px-6 py-5">
              <span className="font-heading text-2xl font-normal text-heading tracking-[-0.768px] leading-none">Invite Links</span>
              <Btn3DOrange onClick={createInvite} className={createInviteMutation.isPending ? 'opacity-50 pointer-events-none' : ''}>
                <PlusIcon size={16} color="white" /> {createInviteMutation.isPending ? 'Creating...' : 'Create invite'}
              </Btn3DOrange>
            </div>
            <div className="px-6 pb-5">
              {invites.length === 0 ? (
                <div className="border border-border rounded-xl flex flex-col items-center justify-center p-8 gap-2">
                  <UserIcon />
                  <span className="text-[11px] font-semibold text-muted text-center tracking-[-0.165px] leading-[1.2]">No active invite codes. Create one to invite members.</span>
                </div>
              ) : (
                <div className="flex flex-col gap-4">
                  {invites.map((invite) => (
                    <div key={invite.id} className="bg-bg border border-border rounded-xl flex items-center justify-between p-3 overflow-hidden">
                      <div className="flex flex-col gap-1">
                        <span className="text-sm font-semibold text-heading leading-[1.2]">Invite link</span>
                        <span className="text-[11px] font-normal text-muted leading-[1.2]">
                          Role: {invite.default_role}
                          {invite.expires_at && ` · Expires ${new Date(invite.expires_at).toLocaleDateString()}`}
                          {invite.max_uses !== null && ` · ${invite.use_count}/${invite.max_uses} used`}
                        </span>
                      </div>
                      <div className="flex items-center gap-3">
                        <button onClick={() => copyInvite(invite.code)} className="bg-surface border border-border rounded-lg px-4 py-2 flex items-center gap-2 cursor-pointer self-stretch focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none">
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--color-heading)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><rect width="14" height="14" x="8" y="8" rx="2" ry="2" /><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2" /></svg>
                          <span className="text-sm font-semibold text-heading font-sans leading-[1.2]">{invite.code}</span>
                        </button>
                        <button
                          onClick={() => removeInvite(invite.id)}
                          className="bg-transparent border-none cursor-pointer p-0 flex items-center justify-center shrink-0 focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none"
                        >
                          <CloseIcon size={16} color="var(--color-muted)" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Danger Zone */}
          <div className="bg-surface border border-border rounded-2xl overflow-hidden">
            <div className="px-6 py-5 flex flex-col gap-2">
              <span className="font-heading text-2xl font-normal text-heading tracking-[-0.768px] leading-none">Danger Zone</span>
              <span className="text-sm font-normal text-body leading-[1.2]">Removing your organization will cancel all active policies and disable your account.</span>
            </div>
            <div className="px-6 pb-5">
              <BtnDanger onClick={() => setRemoveOrgOpen(true)}>
                Remove organization
              </BtnDanger>
            </div>
          </div>
        </div>
      </div>

      {/* Edit Org Modal */}
      <Modal open={editOrgOpen} onClose={() => setEditOrgOpen(false)} width={440}>
        <div className="p-6 flex flex-col gap-5">
          <div className="flex items-start justify-between">
            <div className="font-heading text-2xl font-normal text-heading tracking-[-0.768px] leading-none">Edit organization</div>
            <button onClick={() => setEditOrgOpen(false)} className="bg-transparent border-none cursor-pointer p-0 leading-none shrink-0"><CloseIcon /></button>
          </div>
          <div className="flex flex-col gap-4">
            <div><Label>Organization name</Label><Input value={orgName} onChange={(e) => setOrgName(e.target.value)} /></div>
            <div><Label>Contact email</Label><Input type="email" value={orgEmail} onChange={(e) => setOrgEmail(e.target.value)} placeholder="billing@company.com" /></div>
            <div><Label>Phone</Label><Input type="tel" value={orgPhone} onChange={(e) => setOrgPhone(e.target.value)} placeholder="(555) 123-4567" /></div>
            <div><Label>Website</Label><Input type="url" value={orgWebsite} onChange={(e) => setOrgWebsite(e.target.value)} placeholder="https://company.com" /></div>
          </div>
          <div className="flex gap-2">
            <Btn3DWhite fullWidth onClick={() => setEditOrgOpen(false)}>Cancel</Btn3DWhite>
            <Btn3DOrange fullWidth onClick={handleSaveOrg} disabled={updateOrgMutation.isPending}>
              {updateOrgMutation.isPending ? 'Saving...' : 'Save changes'}
            </Btn3DOrange>
          </div>
        </div>
      </Modal>

      {/* Remove Org Modal */}
      <Modal open={removeOrgOpen} onClose={() => setRemoveOrgOpen(false)} width={440}>
        <div className="p-6 flex flex-col items-center gap-4 text-center">
          <div className="w-12 h-12 rounded-full bg-danger-bg flex items-center justify-center">
            <AlertCircleIcon />
          </div>
          <div>
            <div className="font-heading text-2xl font-normal text-heading tracking-[-0.768px] leading-none mb-2">Remove organization?</div>
            <div className="text-sm font-normal text-muted leading-[1.5] max-w-80 mx-auto">
              This will cancel all active policies and disable the account for <strong className="text-heading">{org?.name}</strong>. Associated certificates and claims will no longer be accessible.
            </div>
          </div>
          <div className="flex gap-2 w-full">
            <Btn3DWhite fullWidth onClick={() => setRemoveOrgOpen(false)}>Cancel</Btn3DWhite>
            <BtnDangerConfirm onClick={handleRemoveOrg}>
              {leaveOrgMutation.isPending ? 'Removing...' : 'Remove'}
            </BtnDangerConfirm>
          </div>
        </div>
      </Modal>

      {/* Invite Member Modal */}
      <Modal open={inviteMemberOpen} onClose={() => setInviteMemberOpen(false)} width={440}>
        <div className="p-6 flex flex-col gap-5">
          <div className="flex items-start justify-between">
            <div className="font-heading text-2xl font-normal text-heading tracking-[-0.768px] leading-none">Invite Member</div>
            <button onClick={() => setInviteMemberOpen(false)} className="bg-transparent border-none cursor-pointer p-0 leading-none shrink-0"><CloseIcon /></button>
          </div>
          <div className="flex flex-col gap-4">
            <div>
              <Label>Email address</Label>
              <Input
                type="email"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                placeholder="colleague@company.com"
              />
            </div>
            <div>
              <Label>Role</Label>
              <CustomSelect
                value={inviteRole}
                onChange={(val) => setInviteRole(val as 'viewer' | 'editor' | 'owner')}
                options={[
                  { value: 'viewer', label: 'Viewer', description: 'Can view policies and quotes' },
                  { value: 'editor', label: 'Editor', description: 'Can create and edit quotes' },
                  { value: 'owner', label: 'Owner', description: 'Full access including team management' },
                ]}
              />
            </div>
          </div>
          <div className="flex gap-2">
            <Btn3DWhite fullWidth onClick={() => setInviteMemberOpen(false)}>Cancel</Btn3DWhite>
            <Btn3DOrange
              fullWidth
              onClick={handleInviteMember}
              disabled={createInviteMutation.isPending || !inviteEmail.trim()}
            >
              {createInviteMutation.isPending ? 'Sending...' : 'Send Invite'}
            </Btn3DOrange>
          </div>
        </div>
      </Modal>
    </div>
  );
}
