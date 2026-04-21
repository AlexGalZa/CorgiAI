'use client';

import { useState } from 'react';
import { apiFetch } from '@/lib/api';
import { useAppStore } from '@/stores/use-app-store';

// ─── Types ────────────────────────────────────────────────────────────────────

interface GapRecommendation {
  coverage_slug: string;
  coverage_name: string;
  reason: string;
  risk_level: 'low' | 'medium' | 'high';
  urgency: 'immediate' | 'soon' | 'optional';
  industry_adoption: string;
  description: string;
}

interface CoverageGapResult {
  summary: string;
  risk_score: 'low' | 'medium' | 'high';
  recommended_coverages: GapRecommendation[];
  current_coverage_slugs: string[];
  company_name: string;
  analysis_method: 'ai' | 'rules';
}

const RISK_COLORS = {
  low: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  medium: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  high: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
};

const URGENCY_LABELS = {
  immediate: { label: 'Immediate', color: 'text-red-600 dark:text-red-400' },
  soon: { label: 'Soon', color: 'text-amber-600 dark:text-amber-400' },
  optional: { label: 'Optional', color: 'text-muted' },
};

const RISK_SCORE_COPY = {
  low: { emoji: '🟢', label: 'Well covered', desc: 'Your coverage looks good for your company size and industry.' },
  medium: { emoji: '🟡', label: 'Some gaps', desc: 'You have some coverage gaps worth addressing.' },
  high: { emoji: '🔴', label: 'Significant gaps', desc: 'Your company has several important coverage gaps.' },
};

// ─── Main Component ───────────────────────────────────────────────────────────

export default function CoverageGapAnalysis() {
  const { showToast } = useAppStore();
  const [industry, setIndustry] = useState('');
  const [employeeCount, setEmployeeCount] = useState('');
  const [annualRevenue, setAnnualRevenue] = useState('');
  const [description, setDescription] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<CoverageGapResult | null>(null);

  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!industry.trim()) {
      showToast('Please enter your industry');
      return;
    }

    setIsAnalyzing(true);
    setResult(null);

    try {
      const data = await apiFetch<CoverageGapResult>('/api/v1/analysis/coverage-gap', {
        method: 'POST',
        body: {
          industry: industry.trim(),
          employee_count: parseInt(employeeCount) || 1,
          annual_revenue: parseFloat(annualRevenue) || 0,
          description: description.trim(),
          current_coverage_slugs: [],
        },
      });
      setResult(data);
    } catch {
      showToast('Analysis failed. Please try again.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const scoreInfo = result ? RISK_SCORE_COPY[result.risk_score] : null;

  return (
    <div className="rounded-2xl border border-border bg-surface overflow-hidden">
      {/* Header */}
      <div className="px-6 py-5 border-b border-border flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-primary/10 flex items-center justify-center">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
            <line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
        </div>
        <div>
          <h3 className="text-sm font-semibold text-heading">Coverage Gap Analysis</h3>
          <p className="text-xs text-muted">AI-powered analysis based on your industry and company profile</p>
        </div>
      </div>

      <div className="p-6">
        {!result ? (
          <form onSubmit={handleAnalyze} className="flex flex-col gap-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-medium text-heading" htmlFor="gap-industry">
                  Industry <span className="text-primary">*</span>
                </label>
                <input
                  id="gap-industry"
                  type="text"
                  value={industry}
                  onChange={(e) => setIndustry(e.target.value)}
                  placeholder="e.g. Technology, Healthcare, SaaS"
                  required
                  className="px-3 py-2 text-sm rounded-lg border border-border bg-input text-body placeholder:text-muted outline-none focus:border-primary transition-colors"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-medium text-heading" htmlFor="gap-employees">
                  Number of employees
                </label>
                <input
                  id="gap-employees"
                  type="number"
                  value={employeeCount}
                  onChange={(e) => setEmployeeCount(e.target.value)}
                  placeholder="e.g. 25"
                  min="1"
                  className="px-3 py-2 text-sm rounded-lg border border-border bg-input text-body placeholder:text-muted outline-none focus:border-primary transition-colors"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-medium text-heading" htmlFor="gap-revenue">
                  Annual revenue (USD)
                </label>
                <input
                  id="gap-revenue"
                  type="number"
                  value={annualRevenue}
                  onChange={(e) => setAnnualRevenue(e.target.value)}
                  placeholder="e.g. 2000000"
                  min="0"
                  className="px-3 py-2 text-sm rounded-lg border border-border bg-input text-body placeholder:text-muted outline-none focus:border-primary transition-colors"
                />
              </div>
              <div className="flex flex-col gap-1.5 sm:col-span-1">
                <label className="text-xs font-medium text-heading" htmlFor="gap-description">
                  What does your company do?
                </label>
                <input
                  id="gap-description"
                  type="text"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Brief description of your business"
                  className="px-3 py-2 text-sm rounded-lg border border-border bg-input text-body placeholder:text-muted outline-none focus:border-primary transition-colors"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isAnalyzing || !industry.trim()}
              className="self-start px-6 py-2.5 bg-primary text-white text-sm font-semibold rounded-xl border-none cursor-pointer hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isAnalyzing ? (
                <>
                  <svg className="animate-spin" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
                  </svg>
                  Analyzing…
                </>
              ) : (
                <>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
                  </svg>
                  Analyze my coverage
                </>
              )}
            </button>
          </form>
        ) : (
          <div className="flex flex-col gap-6">
            {/* Score summary */}
            <div className={`rounded-xl p-4 flex items-start gap-3 ${RISK_COLORS[result.risk_score]}`}>
              <span className="text-2xl">{scoreInfo?.emoji}</span>
              <div>
                <p className="text-sm font-semibold">{scoreInfo?.label}</p>
                <p className="text-sm mt-0.5">{result.summary}</p>
                {result.analysis_method === 'ai' && (
                  <p className="text-xs mt-1 opacity-70">✨ Powered by AI</p>
                )}
              </div>
            </div>

            {/* Current coverage */}
            {result.current_coverage_slugs.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold uppercase tracking-wider text-muted mb-2">Current coverage</h4>
                <div className="flex flex-wrap gap-2">
                  {result.current_coverage_slugs.map((slug) => (
                    <span key={slug} className="flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 font-medium">
                      <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="20 6 9 17 4 12"/>
                      </svg>
                      {slug.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Recommendations */}
            {result.recommended_coverages.length > 0 ? (
              <div>
                <h4 className="text-xs font-semibold uppercase tracking-wider text-muted mb-3">Recommended additions</h4>
                <div className="flex flex-col gap-3">
                  {result.recommended_coverages.map((rec) => (
                    <div key={rec.coverage_slug} className="rounded-xl border border-border p-4 flex gap-4 items-start">
                      <div className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${
                        rec.risk_level === 'high' ? 'bg-red-500' :
                        rec.risk_level === 'medium' ? 'bg-amber-500' : 'bg-green-500'
                      }`} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-2 flex-wrap">
                          <p className="text-sm font-semibold text-heading">{rec.coverage_name}</p>
                          <span className={`text-xs font-medium ${URGENCY_LABELS[rec.urgency]?.color}`}>
                            {URGENCY_LABELS[rec.urgency]?.label}
                          </span>
                        </div>
                        <p className="text-xs text-muted mt-1">{rec.reason}</p>
                        {rec.industry_adoption && (
                          <p className="text-xs text-muted mt-1 italic">{rec.industry_adoption}</p>
                        )}
                        <a
                          href="/quotes"
                          className="inline-flex items-center gap-1 text-xs text-primary font-medium mt-2 hover:underline no-underline"
                        >
                          Get a quote
                          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>
                          </svg>
                        </a>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="text-center py-4">
                <p className="text-sm font-medium text-green-600 dark:text-green-400">
                  🎉 No significant coverage gaps found!
                </p>
                <p className="text-xs text-muted mt-1">Your coverage looks comprehensive for your company profile.</p>
              </div>
            )}

            {/* Reset */}
            <button
              onClick={() => setResult(null)}
              className="self-start text-xs text-muted hover:text-body transition-colors bg-transparent border-none cursor-pointer p-0 flex items-center gap-1"
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-4.3"/>
              </svg>
              Run new analysis
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
