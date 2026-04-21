'use client';

import { Suspense, useState, useRef, useEffect } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useLogin, useVerifyCode, usePasswordLogin } from '@/hooks/use-auth';
import { useAuthStore } from '@/stores/use-auth-store';
import AuthHero from '@/components/layout/AuthHero';
import { Input } from '@/components/ui/input';
import { BtnDark } from '@/components/ui/button';

const DEV_ACCOUNTS = [
  { label: 'Sergio Garcia', email: 'sergio@corgi.com' },
  { label: 'Admin User', email: 'admin@corgi.com' },
  { label: 'Broker Partner', email: 'broker@corgi.com' },
];

type Step = 'email' | 'method' | 'otp' | 'password';

export default function LoginPage() {
  return (
    <Suspense fallback={<AuthHero><div /></AuthHero>}>
      <LoginContent />
    </Suspense>
  );
}

function LoginContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirectParam = searchParams.get('redirect');

  const [step, setStep] = useState<Step>('email');
  const [email, setEmail] = useState('');
  const [emailError, setEmailError] = useState('');
  const [password, setPassword] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [otp, setOtp] = useState<string[]>(['', '', '', '', '', '']);
  const [otpError, setOtpError] = useState('');
  const [countdown, setCountdown] = useState(0);
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  const loginMutation = useLogin();
  const verifyCode = useVerifyCode();
  const passwordLogin = usePasswordLogin();

  useEffect(() => {
    if (countdown <= 0) return;
    const t = setTimeout(() => setCountdown((c) => c - 1), 1000);
    return () => clearTimeout(t);
  }, [countdown]);

  useEffect(() => {
    if (step === 'otp') {
      setTimeout(() => inputRefs.current[0]?.focus(), 50);
    }
  }, [step]);

  const validateEmail = (val: string) => {
    if (!val.trim()) return 'Email is required';
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val)) return 'Invalid email address';
    return '';
  };

  const handleContinue = () => {
    const err = validateEmail(email);
    if (err) { setEmailError(err); return; }
    setEmailError('');
    setStep('method');
  };

  const handleChooseOtp = () => {
    loginMutation.mutate(email, {
      onSuccess: () => {
        setStep('otp');
        setCountdown(60);
      },
      onError: (error) => {
        setEmailError(error.message);
        setStep('email');
      },
    });
  };

  const handleChoosePassword = () => {
    setStep('password');
    setPasswordError('');
    setPassword('');
  };

  const handlePasswordSubmit = () => {
    if (!password) { setPasswordError('Password is required'); return; }
    setPasswordError('');
    passwordLogin.mutate(
      { email, password },
      { onError: (error) => setPasswordError(error.message || 'Invalid email or password') },
    );
  };

  const handleResend = () => {
    if (countdown > 0) return;
    loginMutation.mutate(email, { onSuccess: () => setCountdown(60) });
  };

  const handleOtpChange = (index: number, value: string) => {
    if (value && !/^\d$/.test(value)) return;
    setOtpError('');
    const newOtp = [...otp];
    newOtp[index] = value;
    setOtp(newOtp);
    if (value && index < 5) inputRefs.current[index + 1]?.focus();
    if (value && index === 5) {
      const code = newOtp.join('');
      if (code.length === 6) handleVerify(code);
    }
  };

  const handleOtpKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Backspace' && !otp[index] && index > 0) inputRefs.current[index - 1]?.focus();
  };

  const handleOtpPaste = (e: React.ClipboardEvent) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
    if (!pasted) return;
    const newOtp = [...otp];
    for (let i = 0; i < 6; i++) newOtp[i] = pasted[i] || '';
    setOtp(newOtp);
    inputRefs.current[Math.min(pasted.length, 5)]?.focus();
    if (pasted.length === 6) handleVerify(pasted);
  };

  const handleVerify = (code?: string) => {
    const finalCode = code || otp.join('');
    if (finalCode.length !== 6) { setOtpError('Enter all 6 digits'); return; }
    verifyCode.mutate(
      { email, code: finalCode },
      {
        onError: (error) => {
          setOtpError(error.message || 'Invalid or expired code');
          setOtp(['', '', '', '', '', '']);
          inputRefs.current[0]?.focus();
        },
      },
    );
  };

  const isLoading = loginMutation.isPending || verifyCode.isPending || passwordLogin.isPending;
  const registerHref = redirectParam ? `/register?redirect=${encodeURIComponent(redirectParam)}` : '/register';

  return (
    <AuthHero>
      <div className="w-full">
        {/* Step: Email */}
        {step === 'email' && (
          <div className="flex flex-col gap-4">
            <h1 className="font-heading text-[32px] md:text-[36px] font-medium text-heading tracking-[-1.024px] leading-[1.05] mb-2">
              Welcome back.
            </h1>
            <p className="text-sm md:text-base text-body leading-[1.6] mb-2">
              Sign in to manage your policies, certificates, and claims.
            </p>
            <Input
              type="email"
              value={email}
              onChange={(e) => { setEmail(e.target.value); if (emailError) setEmailError(''); }}
              placeholder="Enter your email"
              onKeyDown={(e) => e.key === 'Enter' && handleContinue()}
              autoFocus
              error={!!emailError}
            />
            {emailError && <p className="text-danger text-sm m-0">{emailError}</p>}
            <BtnDark fullWidth onClick={handleContinue} disabled={isLoading}>
              Continue
            </BtnDark>
            <p className="text-center text-sm text-muted m-0">
              Don&apos;t have an account?{' '}
              <Link href={registerHref} className="text-heading font-semibold no-underline">Register</Link>
            </p>
          </div>
        )}

        {/* Step: Choose method */}
        {step === 'method' && (
          <div className="flex flex-col gap-4">
            <h1 className="text-xl font-bold text-heading leading-tight">Choose sign-in method</h1>
            <p className="text-muted text-sm m-0">Signing in as <strong>{email}</strong></p>
            <div className="flex flex-col gap-2.5">
              <button
                className="flex items-center gap-4 py-3.5 px-4 border border-border rounded-xl cursor-pointer bg-surface text-left transition-[border-color,box-shadow] font-sans w-full hover:border-border-accent focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none"
                onClick={handleChooseOtp}
                disabled={isLoading}
              >
                <div className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0 bg-bg">
                  <svg width={20} height={20} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" className="text-muted">
                    <rect width={20} height={16} x={2} y={4} rx={2} />
                    <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
                  </svg>
                </div>
                <div className="flex-1">
                  <div className="font-semibold text-sm text-heading">Email code</div>
                  <div className="text-xs text-muted mt-0.5">We&apos;ll send a 6-digit code to your email</div>
                </div>
              </button>

              <button
                className="flex items-center gap-4 py-3.5 px-4 border border-border rounded-xl cursor-pointer bg-surface text-left transition-[border-color,box-shadow] font-sans w-full hover:border-border-accent focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none"
                onClick={handleChoosePassword}
                disabled={isLoading}
              >
                <div className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0 bg-bg">
                  <svg width={20} height={20} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" className="text-muted">
                    <rect width={18} height={11} x={3} y={11} rx={2} ry={2} />
                    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                  </svg>
                </div>
                <div className="flex-1">
                  <div className="font-semibold text-sm text-heading">Password</div>
                  <div className="text-xs text-muted mt-0.5">Sign in with your account password</div>
                </div>
              </button>
            </div>

            <button
              className="inline-flex items-center gap-1.5 py-2 px-3.5 border border-border rounded-xl bg-surface cursor-pointer font-sans text-sm font-medium text-heading transition-[border-color,box-shadow] w-fit hover:border-border-accent focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none"
              onClick={() => setStep('email')}
            >
              &larr; Back
            </button>
          </div>
        )}

        {/* Step: OTP */}
        {step === 'otp' && (
          <div className="flex flex-col gap-4">
            <h1 className="text-xl font-bold text-heading leading-tight">Enter code</h1>
            <p className="text-muted text-sm m-0">We sent a 6-digit code to <strong>{email}</strong></p>

            <div className="flex gap-2" onPaste={handleOtpPaste}>
              {otp.map((digit, i) => (
                <input
                  key={i}
                  ref={(el) => { inputRefs.current[i] = el; }}
                  type="text"
                  inputMode="numeric"
                  maxLength={1}
                  value={digit}
                  onChange={(e) => handleOtpChange(i, e.target.value)}
                  onKeyDown={(e) => handleOtpKeyDown(i, e)}
                  className={`w-full max-w-[48px] aspect-square text-center text-xl font-semibold font-mono border rounded-xl outline-none transition-[border-color,box-shadow] bg-surface text-heading focus:border-heading ${otpError ? 'border-danger' : 'border-border'}`}
                />
              ))}
            </div>
            {otpError && <p className="text-danger text-sm m-0">{otpError}</p>}

            <BtnDark fullWidth onClick={() => handleVerify()} disabled={isLoading || otp.join('').length !== 6}>
              {verifyCode.isPending ? 'Verifying...' : 'Verify'}
            </BtnDark>

            <div className="flex justify-between items-center">
              <button
                className="inline-flex items-center gap-1.5 py-2 px-3.5 border border-border rounded-xl bg-surface cursor-pointer font-sans text-sm font-medium text-heading transition-[border-color,box-shadow] w-fit hover:border-border-accent focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none"
                onClick={() => { setStep('method'); setOtp(['', '', '', '', '', '']); setOtpError(''); }}
              >
                &larr; Back
              </button>
              <button
                onClick={handleResend}
                disabled={countdown > 0}
                className={`bg-transparent border-none text-xs font-medium font-sans focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none ${countdown > 0 ? 'text-muted cursor-default' : 'text-heading cursor-pointer'}`}
              >
                {countdown > 0 ? `Resend in ${countdown}s` : 'Resend code'}
              </button>
            </div>
          </div>
        )}

        {/* Step: Password */}
        {step === 'password' && (
          <div className="flex flex-col gap-4">
            <h1 className="text-xl font-bold text-heading leading-tight">Enter password</h1>
            <p className="text-muted text-sm m-0">Signing in as <strong>{email}</strong></p>

            <Input
              type="password"
              value={password}
              onChange={(e) => { setPassword(e.target.value); if (passwordError) setPasswordError(''); }}
              placeholder="Enter your password"
              onKeyDown={(e) => e.key === 'Enter' && handlePasswordSubmit()}
              autoFocus
              error={!!passwordError}
            />
            {passwordError && <p className="text-danger text-sm m-0">{passwordError}</p>}

            <BtnDark fullWidth onClick={handlePasswordSubmit} disabled={isLoading}>
              {passwordLogin.isPending ? 'Signing in...' : 'Sign in'}
            </BtnDark>

            <button
              className="inline-flex items-center gap-1.5 py-2 px-3.5 border border-border rounded-xl bg-surface cursor-pointer font-sans text-sm font-medium text-heading transition-[border-color,box-shadow] w-fit hover:border-border-accent focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none"
              onClick={() => { setStep('method'); setPasswordError(''); }}
            >
              &larr; Back
            </button>
          </div>
        )}

        {/* Dev quick login */}
        {process.env.NODE_ENV === 'development' && step === 'email' && (
          <div className="mt-6 border-t border-border pt-4">
            <div className="text-xs font-semibold uppercase tracking-wider text-muted mb-2">Your accounts</div>
            {DEV_ACCOUNTS.map((acc) => (
              <DevLoginButton key={acc.email} account={acc} />
            ))}
          </div>
        )}
      </div>
    </AuthHero>
  );
}

function DevLoginButton({ account }: { account: { label: string; email: string } }) {
  const [loading, setLoading] = useState(false);
  const setAuth = useAuthStore((s) => s.setAuth);
  const router = useRouter();

  const handleQuickLogin = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/users/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: account.email, password: 'corgi123' }),
      });
      const data = await res.json();
      if (data.data) {
        setAuth(data.data.user, data.data.tokens);
        router.push('/');
      }
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      onClick={handleQuickLogin}
      disabled={loading}
      className="flex items-center gap-2 w-full py-2 px-3 border border-border rounded-xl bg-surface cursor-pointer font-sans text-sm text-heading transition-colors mb-1.5 text-left hover:border-border-accent focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none"
    >
      <div className="w-7 h-7 rounded-full bg-heading text-white flex items-center justify-center text-[0.72rem] font-semibold shrink-0">
        {account.label.charAt(0).toUpperCase()}
      </div>
      <span className="flex-1 text-sm text-heading">{account.label}</span>
      <span className="text-[0.7rem] text-muted">
        {loading ? 'Signing in...' : account.email}
      </span>
    </button>
  );
}
