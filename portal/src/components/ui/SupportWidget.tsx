'use client';

import { useState, useRef, useEffect } from 'react';
import { useAuthStore } from '@/stores/use-auth-store';
import { useAppStore } from '@/stores/use-app-store';

interface SupportWidgetProps {
  slackWebhookUrl?: string;
}

export default function SupportWidget({ slackWebhookUrl }: SupportWidgetProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [message, setMessage] = useState('');
  const [subject, setSubject] = useState('');
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const { user } = useAuthStore();
  const { showToast } = useAppStore();
  const panelRef = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim()) return;

    setSending(true);

    const webhookUrl =
      slackWebhookUrl ||
      process.env.NEXT_PUBLIC_SLACK_WEBHOOK_URL;

    const payload = {
      text: `*New Support Request from Portal*`,
      blocks: [
        {
          type: 'header',
          text: {
            type: 'plain_text',
            text: '🐕 New Support Request',
            emoji: true,
          },
        },
        {
          type: 'section',
          fields: [
            {
              type: 'mrkdwn',
              text: `*From:*\n${user?.email || 'Unknown'}`,
            },
            {
              type: 'mrkdwn',
              text: `*Subject:*\n${subject || 'General Inquiry'}`,
            },
          ],
        },
        {
          type: 'section',
          text: {
            type: 'mrkdwn',
            text: `*Message:*\n${message}`,
          },
        },
      ],
    };

    try {
      if (webhookUrl) {
        await fetch(webhookUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
          mode: 'no-cors',
        });
      } else {
        // Fallback: log to console in dev mode
        console.info('[SupportWidget] No webhook URL configured. Message:', payload);
      }

      setSent(true);
      showToast('Message sent! We\'ll get back to you shortly.');
      setTimeout(() => {
        setIsOpen(false);
        setSent(false);
        setMessage('');
        setSubject('');
      }, 2000);
    } catch {
      showToast('Failed to send message. Please email support@corginsurance.com');
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-3">
      {/* Support panel */}
      {isOpen && (
        <div
          ref={panelRef}
          className="w-[340px] rounded-2xl border border-border bg-bg shadow-2xl overflow-hidden animate-in slide-in-from-bottom-4 duration-200"
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 bg-primary text-white">
            <div className="flex items-center gap-2">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2C6.48 2 2 6.48 2 12c0 1.54.36 2.98.97 4.29L1 23l6.71-1.97C9.02 21.64 10.46 22 12 22c5.52 0 10-4.48 10-10S17.52 2 12 2zm0 18c-1.43 0-2.8-.38-4-.99l-.28-.17-2.91.85.84-2.85-.19-.29A7.93 7.93 0 0 1 4 12c0-4.41 3.59-8 8-8s8 3.59 8 8-3.59 8-8 8z"/>
              </svg>
              <span className="text-sm font-semibold">Talk to us</span>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="text-white/80 hover:text-white transition-colors bg-transparent border-none cursor-pointer p-0"
              aria-label="Close support panel"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </div>

          {/* Body */}
          <div className="p-4">
            {sent ? (
              <div className="flex flex-col items-center gap-3 py-6 text-center">
                <div className="w-12 h-12 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-green-600 dark:text-green-400">
                    <polyline points="20 6 9 17 4 12"/>
                  </svg>
                </div>
                <p className="text-sm font-medium text-heading">Message sent!</p>
                <p className="text-xs text-muted">We'll get back to you shortly.</p>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="flex flex-col gap-3">
                <p className="text-xs text-muted">
                  Send us a message and we'll get back to you as soon as possible.
                </p>

                {user?.email && (
                  <div className="text-xs text-muted flex items-center gap-1">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
                    </svg>
                    Sending as <span className="font-medium text-body ml-1">{user.email}</span>
                  </div>
                )}

                <div className="flex flex-col gap-1">
                  <label className="text-xs font-medium text-heading" htmlFor="support-subject">
                    Subject
                  </label>
                  <input
                    id="support-subject"
                    type="text"
                    value={subject}
                    onChange={(e) => setSubject(e.target.value)}
                    placeholder="e.g. Question about my policy"
                    className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-input text-body placeholder:text-muted outline-none focus:border-primary transition-colors"
                  />
                </div>

                <div className="flex flex-col gap-1">
                  <label className="text-xs font-medium text-heading" htmlFor="support-message">
                    Message <span className="text-primary">*</span>
                  </label>
                  <textarea
                    id="support-message"
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    placeholder="How can we help you?"
                    required
                    rows={4}
                    className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-input text-body placeholder:text-muted outline-none focus:border-primary transition-colors resize-none"
                  />
                </div>

                <button
                  type="submit"
                  disabled={sending || !message.trim()}
                  className="w-full py-2 px-4 bg-primary text-white text-sm font-semibold rounded-lg border-none cursor-pointer hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {sending ? 'Sending…' : 'Send message'}
                </button>

                <p className="text-xs text-muted text-center">
                  Or email us at{' '}
                  <a href="mailto:support@corginsurance.com" className="text-primary hover:underline">
                    support@corginsurance.com
                  </a>
                </p>
              </form>
            )}
          </div>
        </div>
      )}

      {/* Floating button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-14 h-14 rounded-full bg-primary text-white shadow-lg border-none cursor-pointer flex items-center justify-center hover:bg-primary/90 hover:scale-105 transition-all duration-200 active:scale-95"
        aria-label={isOpen ? 'Close support' : 'Open support chat'}
      >
        {isOpen ? (
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        ) : (
          <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2C6.48 2 2 6.48 2 12c0 1.54.36 2.98.97 4.29L1 23l6.71-1.97C9.02 21.64 10.46 22 12 22c5.52 0 10-4.48 10-10S17.52 2 12 2zm0 18c-1.43 0-2.8-.38-4-.99l-.28-.17-2.91.85.84-2.85-.19-.29A7.93 7.93 0 0 1 4 12c0-4.41 3.59-8 8-8s8 3.59 8 8-3.59 8-8 8z"/>
          </svg>
        )}
      </button>
    </div>
  );
}
