'use client';

import { Suspense, useState } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { useRegister } from '@/hooks/use-auth';
import AuthHero from '@/components/layout/AuthHero';
import { Input } from '@/components/ui/input';
import { BtnDark } from '@/components/ui/button';

export default function RegisterPage() {
  return (
    <Suspense fallback={<AuthHero><div /></AuthHero>}>
      <RegisterContent />
    </Suspense>
  );
}

function RegisterContent() {
  const searchParams = useSearchParams();
  const redirectParam = searchParams.get('redirect');

  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [company, setCompany] = useState('');
  const [phone, setPhone] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [serverError, setServerError] = useState('');

  const register = useRegister();

  const validate = (): boolean => {
    const errs: Record<string, string> = {};
    if (!firstName.trim()) errs.first_name = 'First name is required';
    if (!lastName.trim()) errs.last_name = 'Last name is required';
    if (!email.trim()) errs.email = 'Email is required';
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) errs.email = 'Invalid email address';
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleRegister = () => {
    if (!validate()) return;
    setServerError('');

    register.mutate(
      {
        email: email.trim(),
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        company_name: company.trim() || undefined,
        phone_number: phone.trim() || undefined,
      },
      {
        onError: (error) => {
          setServerError(error.message || 'Registration failed');
        },
      },
    );
  };

  const isReady = firstName.trim() && lastName.trim() && email.trim();
  const loginHref = redirectParam ? `/login?redirect=${encodeURIComponent(redirectParam)}` : '/login';

  const labelBase = 'block text-xs font-semibold text-heading mb-1';

  return (
    <AuthHero>
      <div className="flex flex-col gap-4">
        <h1 className="font-heading text-[32px] md:text-[36px] font-medium text-heading tracking-[-1.024px] leading-[1.05] mb-1">
          Let&apos;s get you set up.
        </h1>
        <p className="text-sm md:text-base text-body leading-[1.6] mb-2">
          A few quick details and you&apos;re ready to manage your policies, certificates, and claims.
        </p>

          {serverError && (
            <div className="bg-danger-bg border border-danger rounded-xl px-3 py-2">
              <p className="text-danger text-sm m-0">{serverError}</p>
            </div>
          )}

          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className={labelBase}>First name</label>
              <Input
                value={firstName}
                onChange={(e) => { setFirstName(e.target.value); if (errors.first_name) setErrors((p) => ({ ...p, first_name: '' })); }}
                placeholder="Jane"
                error={!!errors.first_name}
              />
              {errors.first_name && <p className="text-danger text-xs mt-1">{errors.first_name}</p>}
            </div>
            <div>
              <label className={labelBase}>Last name</label>
              <Input
                value={lastName}
                onChange={(e) => { setLastName(e.target.value); if (errors.last_name) setErrors((p) => ({ ...p, last_name: '' })); }}
                placeholder="Doe"
                error={!!errors.last_name}
              />
              {errors.last_name && <p className="text-danger text-xs mt-1">{errors.last_name}</p>}
            </div>
          </div>

          <div>
            <label className={labelBase}>Work email</label>
            <Input
              type="email"
              value={email}
              onChange={(e) => { setEmail(e.target.value); if (errors.email) setErrors((p) => ({ ...p, email: '' })); }}
              placeholder="jane@acme.com"
              error={!!errors.email}
            />
            {errors.email && <p className="text-danger text-xs mt-1">{errors.email}</p>}
          </div>

          <div>
            <label className={labelBase}>
              Company name <span className="font-normal text-muted">(optional)</span>
            </label>
            <Input
              value={company}
              onChange={(e) => setCompany(e.target.value)}
              placeholder="Acme Inc."
            />
          </div>

          <div>
            <label className={labelBase}>
              Phone <span className="font-normal text-muted">(optional)</span>
            </label>
            <Input
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="+1 (555) 000-0000"
            />
          </div>

          <BtnDark
            fullWidth
            onClick={handleRegister}
            disabled={register.isPending || !isReady}
            className={!isReady ? 'opacity-50' : ''}
          >
            {register.isPending ? 'Creating...' : 'Create account'}
          </BtnDark>

          <p className="text-sm text-muted m-0">
            Already have an account?{' '}
            <Link href={loginHref} className="text-primary font-semibold no-underline hover:underline">Sign in</Link>
          </p>
      </div>
    </AuthHero>
  );
}
