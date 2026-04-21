'use client';

import { useState, useEffect } from 'react';
import { usePageTitle } from '@/hooks/use-page-title';
import { useUser } from '@/hooks/use-auth';
import { useAuthStore } from '@/stores/use-auth-store';
import { useAppStore } from '@/stores/use-app-store';
import { authApi, ApiError } from '@/lib/api';
import { Input, Label } from '@/components/ui/input';
import { BtnPrimary } from '@/components/ui/button';

interface ProfileForm {
  first_name: string;
  last_name: string;
  phone_number: string;
  company_name: string;
}

export default function ProfileSettingsPage() {
  usePageTitle('Profile Settings');

  const { data: user, isLoading } = useUser();
  const updateUser = useAuthStore((s) => s.updateUser);
  const { showToast } = useAppStore();

  const [form, setForm] = useState<ProfileForm>({
    first_name: '',
    last_name: '',
    phone_number: '',
    company_name: '',
  });

  const [errors, setErrors] = useState<Partial<ProfileForm>>({});
  const [saving, setSaving] = useState(false);
  // PATCH /api/v1/users/me does not exist yet
  const ENDPOINT_EXISTS = false;

  // Hydrate form from user data
  useEffect(() => {
    if (user) {
      setForm({
        first_name: user.first_name ?? '',
        last_name: user.last_name ?? '',
        phone_number: user.phone_number ?? '',
        company_name: user.company_name ?? '',
      });
    }
  }, [user]);

  function validate(): boolean {
    const errs: Partial<ProfileForm> = {};
    if (!form.first_name.trim()) errs.first_name = 'First name is required.';
    if (!form.last_name.trim()) errs.last_name = 'Last name is required.';
    setErrors(errs);
    return Object.keys(errs).length === 0;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validate()) return;

    if (!ENDPOINT_EXISTS) {
      showToast('Profile updates coming soon.', 'default');
      return;
    }

    setSaving(true);
    try {
      const updated = await authApi<typeof user>('/api/v1/users/me', {
        method: 'PATCH',
        body: form,
      });
      if (updated) updateUser(updated);
      showToast('Profile saved.', 'default');
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Something went wrong.';
      showToast(msg, 'default');
    } finally {
      setSaving(false);
    }
  }

  if (isLoading) {
    return (
      <div className="flex flex-col gap-4 animate-pulse">
        <div className="h-4 w-32 bg-border rounded" />
        <div className="h-9 bg-border rounded-xl" />
        <div className="h-9 bg-border rounded-xl" />
        <div className="h-9 bg-border rounded-xl" />
      </div>
    );
  }

  return (
    <section className="flex flex-col gap-6">
      <div>
        <h2 className="text-lg font-semibold text-heading">Profile</h2>
        <p className="text-[13px] text-muted mt-0.5">
          Your personal information. Contact support to change your email address.
        </p>
      </div>

      <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-4 max-w-[480px]">
        <div className="grid grid-cols-2 gap-3">
          <div className="flex flex-col gap-1">
            <Label htmlFor="first_name">First name</Label>
            <Input
              id="first_name"
              value={form.first_name}
              onChange={(e) => setForm((f) => ({ ...f, first_name: e.target.value }))}
              error={!!errors.first_name}
              errorId="first_name_error"
              autoComplete="given-name"
            />
            {errors.first_name && (
              <span id="first_name_error" className="text-[11px] text-danger">
                {errors.first_name}
              </span>
            )}
          </div>
          <div className="flex flex-col gap-1">
            <Label htmlFor="last_name">Last name</Label>
            <Input
              id="last_name"
              value={form.last_name}
              onChange={(e) => setForm((f) => ({ ...f, last_name: e.target.value }))}
              error={!!errors.last_name}
              errorId="last_name_error"
              autoComplete="family-name"
            />
            {errors.last_name && (
              <span id="last_name_error" className="text-[11px] text-danger">
                {errors.last_name}
              </span>
            )}
          </div>
        </div>

        <div className="flex flex-col gap-1">
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            value={user?.email ?? ''}
            readOnly
            disabled
            autoComplete="email"
            className="opacity-60 cursor-not-allowed"
          />
          <span className="text-[11px] text-muted">
            Email changes require support.{' '}
            <a
              href="mailto:support@corgiinsure.com?subject=Email change request"
              className="text-primary hover:underline focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none rounded"
            >
              Contact support
            </a>
          </span>
        </div>

        <div className="flex flex-col gap-1">
          <Label htmlFor="phone_number">Phone number</Label>
          <Input
            id="phone_number"
            type="tel"
            value={form.phone_number}
            onChange={(e) => setForm((f) => ({ ...f, phone_number: e.target.value }))}
            autoComplete="tel"
            placeholder="+1 (555) 000-0000"
          />
        </div>

        <div className="flex flex-col gap-1">
          <Label htmlFor="company_name">Company name</Label>
          <Input
            id="company_name"
            value={form.company_name}
            onChange={(e) => setForm((f) => ({ ...f, company_name: e.target.value }))}
            autoComplete="organization"
            placeholder="Acme Corp"
          />
        </div>

        <div className="pt-1">
          <BtnPrimary type="submit" disabled={saving || !ENDPOINT_EXISTS}>
            {!ENDPOINT_EXISTS ? 'Saving soon' : saving ? 'Saving...' : 'Save changes'}
          </BtnPrimary>
        </div>
      </form>
    </section>
  );
}
