'use client';

import { Suspense, useState, useRef, useEffect } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { Btn3DOrange } from '@/components/ui/button';
import { useLogin, useVerifyCode } from '@/hooks/use-auth';
import AuthHero from '@/components/layout/AuthHero';

function VerifyCodeContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const emailParam = searchParams.get('email') || '';

  const [otp, setOtp] = useState<string[]>(['', '', '', '', '', '']);
  const [error, setError] = useState('');
  const [countdown, setCountdown] = useState(60);
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  const login = useLogin();
  const verifyCode = useVerifyCode();

  // Redirect if no email
  useEffect(() => {
    if (!emailParam) {
      router.replace('/login');
    }
  }, [emailParam, router]);

  // Countdown timer
  useEffect(() => {
    if (countdown <= 0) return;
    const t = setTimeout(() => setCountdown((c) => c - 1), 1000);
    return () => clearTimeout(t);
  }, [countdown]);

  // Auto-focus first input
  useEffect(() => {
    setTimeout(() => inputRefs.current[0]?.focus(), 50);
  }, []);

  const handleChange = (index: number, value: string) => {
    if (value && !/^\d$/.test(value)) return;
    setError('');

    const newOtp = [...otp];
    newOtp[index] = value;
    setOtp(newOtp);

    if (value && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }

    if (value && index === 5) {
      const code = newOtp.join('');
      if (code.length === 6) handleVerify(code);
    }
  };

  const handleKeyDown = (index: number, e: React.KeyboardEvent) => {
    if (e.key === 'Backspace' && !otp[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  const handlePaste = (e: React.ClipboardEvent) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
    if (!pasted) return;

    const newOtp = [...otp];
    for (let i = 0; i < 6; i++) newOtp[i] = pasted[i] || '';
    setOtp(newOtp);

    const focusIdx = Math.min(pasted.length, 5);
    inputRefs.current[focusIdx]?.focus();

    if (pasted.length === 6) handleVerify(pasted);
  };

  const handleVerify = (code?: string) => {
    const finalCode = code || otp.join('');
    if (finalCode.length !== 6) {
      setError('Enter all 6 digits');
      return;
    }

    verifyCode.mutate(
      { email: emailParam, code: finalCode },
      {
        onError: (err) => {
          setError(err.message || 'Invalid or expired code');
          setOtp(['', '', '', '', '', '']);
          inputRefs.current[0]?.focus();
        },
      }
    );
  };

  const handleResend = () => {
    if (countdown > 0) return;
    login.mutate(emailParam, {
      onSuccess: () => setCountdown(60),
    });
  };

  if (!emailParam) return null;

  return (
    <div className="w-full">
      <h1 className="font-heading text-[32px] md:text-[36px] font-medium text-heading tracking-[-1.024px] leading-[1.05] mb-2">
        Check your email.
      </h1>
      <p className="text-sm md:text-base text-body leading-[1.6] mb-6">
        We sent a 6-digit code to <strong className="text-heading">{emailParam}</strong>.
      </p>

      <div className="flex flex-col gap-4">
        <div>
          <div className="flex gap-2" onPaste={handlePaste}>
            {otp.map((digit, i) => (
              <input
                key={i}
                ref={(el) => { inputRefs.current[i] = el; }}
                type="text"
                inputMode="numeric"
                maxLength={1}
                value={digit}
                onChange={(e) => handleChange(i, e.target.value)}
                onKeyDown={(e) => handleKeyDown(i, e)}
                className={`w-full aspect-square max-w-[52px] text-center text-lg font-medium border rounded-xl outline-none transition-colors focus:border-primary bg-surface text-heading ${
                  error ? 'border-danger' : 'border-border'
                }`}
              />
            ))}
          </div>
          {error && (
            <p className="text-xs text-danger mt-1">{error}</p>
          )}
        </div>

        <Btn3DOrange
          fullWidth
          onClick={() => handleVerify()}
          disabled={verifyCode.isPending || otp.join('').length !== 6}
        >
          {verifyCode.isPending ? 'Verifying...' : 'Verify & sign in'}
        </Btn3DOrange>

        <div className="flex items-center justify-between">
          <Link
            href="/login"
            className="text-xs font-medium text-muted no-underline hover:text-heading transition-colors"
          >
            Use a different email
          </Link>
          <button
            className={`text-xs font-medium bg-transparent border-none font-sans transition-colors ${
              countdown > 0
                ? 'text-muted cursor-default'
                : 'text-primary cursor-pointer hover:underline'
            }`}
            onClick={handleResend}
            disabled={countdown > 0}
          >
            {countdown > 0 ? `Resend in ${countdown}s` : 'Resend code'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function VerifyCodePage() {
  return (
    <AuthHero>
      <Suspense fallback={<div className="text-sm text-muted">Loading…</div>}>
        <VerifyCodeContent />
      </Suspense>
    </AuthHero>
  );
}
