'use client';

import { useState, useEffect } from 'react';
import { usePageTitle } from '@/hooks/use-page-title';
import { useLogout } from '@/hooks/use-auth';
import { useAppStore } from '@/stores/use-app-store';
import { authApi, ApiError } from '@/lib/api';
import { Input, Label } from '@/components/ui/input';
import { BtnPrimary, BtnSecondary, BtnDanger } from '@/components/ui/button';

// ─── Change password ─────────────────────────────────────────────────────────
// POST /api/v1/users/change-password does not exist yet.
const CHANGE_PW_EXISTS = false;

// ─── TOTP status ─────────────────────────────────────────────────────────────
// GET /api/v1/auth/totp/status  exists.
// POST /api/v1/auth/totp/setup  exists.
// DELETE /api/v1/auth/totp/disable exists.

interface TotpStatusResponse {
  enabled: boolean;
  verified: boolean;
}

interface TotpSetupResponse {
  secret: string;
  provisioning_uri: string;
  qr_data_url?: string | null;
}

function PasswordCard() {
  const { showToast } = useAppStore();
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [confirm, setConfirm] = useState('');
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState<{ current?: string; next?: string; confirm?: string }>({});

  function validate() {
    const errs: typeof errors = {};
    if (!current) errs.current = 'Required.';
    if (!next || next.length < 8) errs.next = 'Minimum 8 characters.';
    if (next !== confirm) errs.confirm = 'Passwords do not match.';
    setErrors(errs);
    return Object.keys(errs).length === 0;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!CHANGE_PW_EXISTS) { showToast('Password changes coming soon.'); return; }
    if (!validate()) return;
    setSaving(true);
    try {
      await authApi('/api/v1/users/change-password', {
        method: 'POST',
        body: { current_password: current, new_password: next },
      });
      showToast('Password updated.');
      setCurrent(''); setNext(''); setConfirm('');
    } catch (err) {
      showToast(err instanceof ApiError ? err.message : 'Something went wrong.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="bg-surface border border-border rounded-2xl p-6 flex flex-col gap-4">
      <div>
        <h3 className="text-base font-semibold text-heading">Change password</h3>
        <p className="text-[13px] text-muted mt-0.5">Use a strong, unique password.</p>
      </div>

      {!CHANGE_PW_EXISTS && (
        <div className="text-[13px] text-muted bg-bg border border-border rounded-xl px-4 py-3">
          Password changes are not yet available in self-service. Contact{' '}
          <a
            href="mailto:support@corgiinsure.com?subject=Password change request"
            className="text-primary hover:underline focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none rounded"
          >
            support
          </a>{' '}
          if you need to reset your password.
        </div>
      )}

      <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-3 max-w-[400px]">
        <div className="flex flex-col gap-1">
          <Label htmlFor="current_password">Current password</Label>
          <Input
            id="current_password"
            type="password"
            value={current}
            onChange={(e) => setCurrent(e.target.value)}
            disabled={!CHANGE_PW_EXISTS}
            autoComplete="current-password"
            error={!!errors.current}
            errorId="current_pw_err"
          />
          {errors.current && <span id="current_pw_err" className="text-[11px] text-danger">{errors.current}</span>}
        </div>
        <div className="flex flex-col gap-1">
          <Label htmlFor="new_password">New password</Label>
          <Input
            id="new_password"
            type="password"
            value={next}
            onChange={(e) => setNext(e.target.value)}
            disabled={!CHANGE_PW_EXISTS}
            autoComplete="new-password"
            error={!!errors.next}
            errorId="new_pw_err"
          />
          {errors.next && <span id="new_pw_err" className="text-[11px] text-danger">{errors.next}</span>}
        </div>
        <div className="flex flex-col gap-1">
          <Label htmlFor="confirm_password">Confirm new password</Label>
          <Input
            id="confirm_password"
            type="password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            disabled={!CHANGE_PW_EXISTS}
            autoComplete="new-password"
            error={!!errors.confirm}
            errorId="confirm_pw_err"
          />
          {errors.confirm && <span id="confirm_pw_err" className="text-[11px] text-danger">{errors.confirm}</span>}
        </div>
        <div className="pt-1">
          <BtnPrimary type="submit" disabled={saving || !CHANGE_PW_EXISTS}>
            {!CHANGE_PW_EXISTS ? 'Coming soon' : saving ? 'Saving...' : 'Update password'}
          </BtnPrimary>
        </div>
      </form>
    </div>
  );
}

// ─── Two-factor authentication card ──────────────────────────────────────────

function TwoFactorCard() {
  const { showToast } = useAppStore();
  const [totpEnabled, setTotpEnabled] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [setupData, setSetupData] = useState<TotpSetupResponse | null>(null);
  const [verifyCode, setVerifyCode] = useState('');
  const [verifyError, setVerifyError] = useState('');

  useEffect(() => {
    authApi<TotpStatusResponse>('/api/v1/auth/totp/status')
      .then((res) => setTotpEnabled(res.enabled && res.verified))
      .catch(() => setTotpEnabled(false))
      .finally(() => setLoading(false));
  }, []);

  async function handleSetup() {
    setWorking(true);
    try {
      const data = await authApi<TotpSetupResponse>('/api/v1/auth/totp/setup', { method: 'POST' });
      setSetupData(data);
    } catch (err) {
      showToast(err instanceof ApiError ? err.message : 'Setup failed.');
    } finally {
      setWorking(false);
    }
  }

  async function handleVerify(e: React.FormEvent) {
    e.preventDefault();
    if (!verifyCode.trim()) { setVerifyError('Enter the 6-digit code.'); return; }
    setVerifyError('');
    setWorking(true);
    try {
      await authApi('/api/v1/auth/totp/verify', { method: 'POST', body: { code: verifyCode } });
      setTotpEnabled(true);
      setSetupData(null);
      setVerifyCode('');
      showToast('Two-factor authentication enabled.');
    } catch (err) {
      setVerifyError(err instanceof ApiError ? err.message : 'Invalid code.');
    } finally {
      setWorking(false);
    }
  }

  async function handleDisable() {
    if (!window.confirm('Disable two-factor authentication? Your account will be less secure.')) return;
    setWorking(true);
    try {
      await authApi('/api/v1/auth/totp/disable', { method: 'DELETE' });
      setTotpEnabled(false);
      showToast('Two-factor authentication disabled.');
    } catch (err) {
      showToast(err instanceof ApiError ? err.message : 'Could not disable 2FA.');
    } finally {
      setWorking(false);
    }
  }

  return (
    <div className="bg-surface border border-border rounded-2xl p-6 flex flex-col gap-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-base font-semibold text-heading">Two-factor authentication</h3>
          <p className="text-[13px] text-muted mt-0.5">
            Add a second layer of security with an authenticator app.
          </p>
        </div>
        {!loading && totpEnabled !== null && !setupData && (
          <div className={`shrink-0 text-[11px] font-semibold px-2.5 py-1 rounded-lg ${totpEnabled ? 'bg-success-bg text-success' : 'bg-bg text-muted border border-border'}`}>
            {totpEnabled ? 'Enabled' : 'Disabled'}
          </div>
        )}
      </div>

      {loading && <div className="h-4 w-24 bg-border rounded animate-pulse" />}

      {!loading && !setupData && (
        <div className="flex gap-3">
          {totpEnabled ? (
            <BtnDanger onClick={handleDisable} disabled={working}>
              {working ? 'Disabling...' : 'Disable 2FA'}
            </BtnDanger>
          ) : (
            <BtnSecondary onClick={handleSetup} disabled={working}>
              {working ? 'Setting up...' : 'Set up 2FA'}
            </BtnSecondary>
          )}
        </div>
      )}

      {setupData && (
        <div className="flex flex-col gap-4">
          <p className="text-[13px] text-body">
            Scan this QR code with your authenticator app (e.g. Google Authenticator, Authy).
          </p>

          {setupData.qr_data_url ? (
            <img
              src={setupData.qr_data_url}
              alt="QR code for authenticator setup"
              className="w-40 h-40 border border-border rounded-xl"
            />
          ) : (
            <div className="bg-bg border border-border rounded-xl px-4 py-3 text-[13px] font-mono text-heading break-all">
              {setupData.provisioning_uri}
            </div>
          )}

          <p className="text-[11px] text-muted">
            Manual entry key: <span className="font-mono text-body">{setupData.secret}</span>
          </p>

          <form onSubmit={handleVerify} noValidate className="flex flex-col gap-2 max-w-[240px]">
            <Label htmlFor="totp_code">Verification code</Label>
            <Input
              id="totp_code"
              type="text"
              inputMode="numeric"
              maxLength={6}
              value={verifyCode}
              onChange={(e) => setVerifyCode(e.target.value.replace(/\D/g, ''))}
              placeholder="000000"
              autoComplete="one-time-code"
              error={!!verifyError}
              errorId="totp_code_err"
            />
            {verifyError && <span id="totp_code_err" className="text-[11px] text-danger">{verifyError}</span>}
            <div className="flex gap-2 pt-1">
              <BtnPrimary type="submit" disabled={working}>
                {working ? 'Verifying...' : 'Verify and enable'}
              </BtnPrimary>
              <BtnSecondary type="button" onClick={() => { setSetupData(null); setVerifyCode(''); setVerifyError(''); }}>
                Cancel
              </BtnSecondary>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}

// ─── Active sessions card ─────────────────────────────────────────────────────

function SessionsCard() {
  const logout = useLogout();
  const { showToast } = useAppStore();
  const [working, setWorking] = useState(false);
  const [done, setDone] = useState(false);

  async function handleSignOutAll() {
    if (!window.confirm('Sign out of all devices? You will be signed out here too.')) return;
    setWorking(true);
    try {
      await authApi('/api/v1/users/sessions', { method: 'DELETE' });
      setDone(true);
      showToast('Signed out of all devices.');
      // Give the toast a moment to show before redirecting
      setTimeout(() => logout(), 1200);
    } catch (err) {
      showToast(err instanceof ApiError ? err.message : 'Could not sign out all sessions.');
      setWorking(false);
    }
  }

  return (
    <div className="bg-surface border border-border rounded-2xl p-6 flex flex-col gap-4">
      <div>
        <h3 className="text-base font-semibold text-heading">Active sessions</h3>
        <p className="text-[13px] text-muted mt-0.5">
          Sign out of all devices if you suspect unauthorized access.
        </p>
      </div>

      {done ? (
        <p className="text-[13px] text-success">Signed out of all devices. Redirecting...</p>
      ) : (
        <BtnDanger onClick={handleSignOutAll} disabled={working}>
          {working ? 'Signing out...' : 'Sign out everywhere'}
        </BtnDanger>
      )}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function SecuritySettingsPage() {
  usePageTitle('Security Settings');

  return (
    <section className="flex flex-col gap-6">
      <div>
        <h2 className="text-lg font-semibold text-heading">Security</h2>
        <p className="text-[13px] text-muted mt-0.5">
          Manage your password, two-factor authentication, and active sessions.
        </p>
      </div>
      <PasswordCard />
      <TwoFactorCard />
      <SessionsCard />
    </section>
  );
}
