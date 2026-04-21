/**
 * Quote flow definitions — step ordering, coverage configs, navigation helpers.
 *
 * Mirrors the reference quoting-form flow.ts but adapted for the portal's
 * dynamic [coverage-slug] route instead of individual hardcoded routes.
 */

// ─── Coverage types ───

export const CoverageTypes = [
  'commercial-general-liability',
  'directors-and-officers',
  'technology-errors-and-omissions',
  'cyber-liability',
  'fiduciary-liability',
  'hired-and-non-owned-auto',
  'media-liability',
  'employment-practices-liability',
] as const;

export type CoverageType = (typeof CoverageTypes)[number];

export const CustomCoverageTypes = [
  'custom-commercial-auto',
  'custom-crime',
  'custom-kidnap-ransom',
  'custom-med-malpractice',
] as const;

export type CustomCoverageType = (typeof CustomCoverageTypes)[number];
export type AllCoverageType = CoverageType | CustomCoverageType;

// ─── Coverage info ───

export interface CoverageInfo {
  id: CoverageType;
  name: string;
  shortName: string;
  description: string;
  includedFeatures: string[];
}

export const Coverages: Record<CoverageType, CoverageInfo> = {
  'commercial-general-liability': {
    id: 'commercial-general-liability',
    name: 'Commercial General Liability',
    shortName: 'CGL',
    description: 'Covers injuries at your business location or damage your work causes to someone else\'s property.',
    includedFeatures: [
      'Protects you from third-party injury or damage claims',
      'Covers everyday business risks',
      'Often required by landlords and customers',
    ],
  },
  'directors-and-officers': {
    id: 'directors-and-officers',
    name: 'Directors & Officers',
    shortName: 'D&O',
    description: 'Protects company leaders if they\'re sued over decisions they make running the business.',
    includedFeatures: [
      'Protects founders, executives, and board decisions',
      'Covers investor and governance-related claims',
      'Helps shield personal assets from lawsuits',
    ],
  },
  'technology-errors-and-omissions': {
    id: 'technology-errors-and-omissions',
    name: 'Tech E&O',
    shortName: 'E&O',
    description: 'Covers you if your technology or service doesn\'t work as promised and causes a customer financial loss.',
    includedFeatures: [
      'Protects you if your product or service fails',
      'Covers customer claims tied to your technology',
      'Helps pay legal defense and settlements',
    ],
  },
  'cyber-liability': {
    id: 'cyber-liability',
    name: 'Cyber Liability',
    shortName: 'Cyber',
    description: 'Helps pay for costs if your business is hacked or customer data is stolen.',
    includedFeatures: [
      'Protects you from data breaches and cyber attacks',
      'Covers notification costs and credit monitoring',
      'Helps pay for legal defense and settlements',
    ],
  },
  'fiduciary-liability': {
    id: 'fiduciary-liability',
    name: 'Fiduciary Liability',
    shortName: 'Fiduciary',
    description: 'Protects you if you\'re accused of mishandling employee benefit plans.',
    includedFeatures: [
      'Protects you when managing benefit plans',
      'Covers claims tied to fiduciary duties',
      'Helps cover defense and penalty exposure',
    ],
  },
  'hired-and-non-owned-auto': {
    id: 'hired-and-non-owned-auto',
    name: 'Hired & Non-Owned Auto',
    shortName: 'HNOA',
    description: 'Covers accidents when employees use their own car, a rental, or a borrowed vehicle for work purposes.',
    includedFeatures: [
      'Protects you if employees drive for work',
      'Covers accidents in personal or rented cars',
      'Helps meet customer or contract requirements',
    ],
  },
  'media-liability': {
    id: 'media-liability',
    name: 'Media Liability',
    shortName: 'Media',
    description: 'Covers claims that your content harmed someone, like defamation, copyright issues, or privacy violations.',
    includedFeatures: [
      'Protects you from marketing or content claims',
      'Covers defamation, copyright, or IP disputes',
      'Helps cover legal defense costs',
    ],
  },
  'employment-practices-liability': {
    id: 'employment-practices-liability',
    name: 'Employment Practices Liability',
    shortName: 'EPL',
    description: 'Protects you if an employee claims things like wrongful termination, harassment, or discrimination.',
    includedFeatures: [
      'Protects you from employee-related lawsuits',
      'Covers claims like termination or discrimination',
      'Helps cover legal defense costs',
    ],
  },
};

export const CustomCoverages: Record<CustomCoverageType, { id: CustomCoverageType; name: string; shortName: string; description: string }> = {
  'custom-commercial-auto': {
    id: 'custom-commercial-auto',
    name: 'Commercial Auto',
    shortName: 'CA',
    description: 'Covers vehicles your business owns if they\'re involved in an accident.',
  },
  'custom-crime': {
    id: 'custom-crime',
    name: 'Crime',
    shortName: 'Crime',
    description: 'Covers losses from employee theft, fraud, or forgery.',
  },
  'custom-kidnap-ransom': {
    id: 'custom-kidnap-ransom',
    name: 'Kidnap & Ransom',
    shortName: 'K&R',
    description: 'Covers costs related to kidnapping, ransom, or extortion involving employees.',
  },
  'custom-med-malpractice': {
    id: 'custom-med-malpractice',
    name: 'Medical Malpractice',
    shortName: 'Med Mal',
    description: 'Protects healthcare providers if they\'re sued for mistakes in patient care.',
  },
};

export const AllCoveragesInfo: Record<AllCoverageType, { name: string; shortName: string; description: string }> = {
  ...Coverages,
  ...CustomCoverages,
};

// ─── Step definitions ───

export type StepId =
  | 'welcome'
  | 'products'
  | 'business-address'
  | 'organization-info'
  | 'financial-details'
  | 'structure-operations'
  | 'coverage-intro'
  | 'directors-and-officers'
  | 'technology-errors-omissions'
  | 'commercial-general-liability'
  | 'cyber-liability'
  | 'fiduciary-liability'
  | 'hired-non-owned-auto'
  | 'media-liability'
  | 'employment-practices-liability'
  | 'loss-history'
  | 'insurance-history'
  | 'notices-signatures'
  | 'summary';

export type FormSection = 'individual' | 'company-info' | 'coverage-forms' | 'claims-history';

export const FormSectionLabels: Record<FormSection, string> = {
  individual: 'Individual',
  'company-info': 'Company',
  'coverage-forms': 'Coverage Forms',
  'claims-history': 'Claims History',
};

export type FormStepStatus = 'completed' | 'current' | 'pending';

export interface FormStep {
  id: StepId;
  path: string;
  name: string;
  section: FormSection;
  coverageType?: AllCoverageType;
  /** Slug for dynamic coverage route */
  coverageSlug?: string;
}

/** Map from coverage-type to the slug used in the URL */
export const CoverageSlugMap: Partial<Record<AllCoverageType, string>> = {
  'directors-and-officers': 'directors-and-officers',
  'technology-errors-and-omissions': 'technology-errors-omissions',
  'commercial-general-liability': 'commercial-general-liability',
  'cyber-liability': 'cyber-liability',
  'fiduciary-liability': 'fiduciary-liability',
  'hired-and-non-owned-auto': 'hired-non-owned-auto',
  'media-liability': 'media-liability',
  'employment-practices-liability': 'employment-practices-liability',
};

export const CoverageOrder: AllCoverageType[] = [
  'directors-and-officers',
  'technology-errors-and-omissions',
  'commercial-general-liability',
  'cyber-liability',
  'fiduciary-liability',
  'hired-and-non-owned-auto',
  'media-liability',
  'employment-practices-liability',
];

export const FormFlow: FormStep[] = [
  // Pre-quote
  { id: 'welcome', path: '/quote/get-started', name: 'Welcome', section: 'individual' },
  { id: 'products', path: '/quote/:quoteNumber/products', name: 'Choose Product(s)', section: 'individual' },

  // Company info
  { id: 'business-address', path: '/quote/:quoteNumber/company/business-address', name: 'Business Address', section: 'company-info' },
  { id: 'organization-info', path: '/quote/:quoteNumber/company/organization-info', name: 'Organization', section: 'company-info' },
  { id: 'financial-details', path: '/quote/:quoteNumber/company/financial-details', name: 'Financial Details', section: 'company-info' },
  { id: 'structure-operations', path: '/quote/:quoteNumber/company/structure-operations', name: 'Structure', section: 'company-info' },

  // Coverage intro
  { id: 'coverage-intro', path: '/quote/:quoteNumber/coverage-intro', name: 'Coverage Intro', section: 'coverage-forms' },

  // Coverage questionnaires (dynamically filtered)
  { id: 'directors-and-officers', path: '/quote/:quoteNumber/directors-and-officers', name: 'D&O', section: 'coverage-forms', coverageType: 'directors-and-officers', coverageSlug: 'directors-and-officers' },
  { id: 'technology-errors-omissions', path: '/quote/:quoteNumber/technology-errors-omissions', name: 'E&O', section: 'coverage-forms', coverageType: 'technology-errors-and-omissions', coverageSlug: 'technology-errors-omissions' },
  { id: 'commercial-general-liability', path: '/quote/:quoteNumber/commercial-general-liability', name: 'CGL', section: 'coverage-forms', coverageType: 'commercial-general-liability', coverageSlug: 'commercial-general-liability' },
  { id: 'cyber-liability', path: '/quote/:quoteNumber/cyber-liability', name: 'Cyber', section: 'coverage-forms', coverageType: 'cyber-liability', coverageSlug: 'cyber-liability' },
  { id: 'fiduciary-liability', path: '/quote/:quoteNumber/fiduciary-liability', name: 'Fiduciary', section: 'coverage-forms', coverageType: 'fiduciary-liability', coverageSlug: 'fiduciary-liability' },
  { id: 'hired-non-owned-auto', path: '/quote/:quoteNumber/hired-non-owned-auto', name: 'HNOA', section: 'coverage-forms', coverageType: 'hired-and-non-owned-auto', coverageSlug: 'hired-non-owned-auto' },
  { id: 'media-liability', path: '/quote/:quoteNumber/media-liability', name: 'Media', section: 'coverage-forms', coverageType: 'media-liability', coverageSlug: 'media-liability' },
  { id: 'employment-practices-liability', path: '/quote/:quoteNumber/employment-practices-liability', name: 'EPL', section: 'coverage-forms', coverageType: 'employment-practices-liability', coverageSlug: 'employment-practices-liability' },

  // Claims history
  { id: 'loss-history', path: '/quote/:quoteNumber/claims-history/loss-history', name: 'Loss History', section: 'claims-history' },
  { id: 'insurance-history', path: '/quote/:quoteNumber/claims-history/insurance-history', name: 'Insurance History', section: 'claims-history' },

  // Final
  { id: 'notices-signatures', path: '/quote/:quoteNumber/notices-signatures', name: 'Notices & Signatures', section: 'individual' },
  { id: 'summary', path: '/quote/:quoteNumber/summary', name: 'Summary', section: 'individual' },
];

// ─── Lookups ───

const StepById = new Map(FormFlow.map((s) => [s.id, s]));
const StepByPath = new Map(FormFlow.map((s) => [s.path, s]));

export function getStep(id: StepId): FormStep | undefined {
  return StepById.get(id);
}

// ─── Flow construction ───

const PreCoverageSteps: FormStep[] = [];
const PostCoverageSteps: FormStep[] = [];
const CoverageSteps: Partial<Record<AllCoverageType, FormStep[]>> = {};

let seenCoverage = false;
for (const step of FormFlow) {
  const isCoverage = step.section === 'coverage-forms' && step.coverageType !== undefined;
  if (isCoverage) {
    seenCoverage = true;
    const ct = step.coverageType as AllCoverageType;
    if (!CoverageSteps[ct]) CoverageSteps[ct] = [];
    CoverageSteps[ct]!.push(step);
  } else {
    if (!seenCoverage) PreCoverageSteps.push(step);
    else PostCoverageSteps.push(step);
  }
}

export function getVisibleSteps(selectedCoverages: AllCoverageType[] = []): FormStep[] {
  const flow: FormStep[] = [...PreCoverageSteps];
  for (const coverageId of CoverageOrder) {
    if (selectedCoverages.includes(coverageId)) {
      const steps = CoverageSteps[coverageId];
      if (steps) flow.push(...steps);
    }
  }
  flow.push(...PostCoverageSteps);
  return flow;
}

export function buildStepPath(step: FormStep, quoteNumber: string): string {
  return step.path.replace(':quoteNumber', quoteNumber);
}

export function getNextStep(currentStepId: StepId, selectedCoverages: AllCoverageType[]): FormStep | undefined {
  const flow = getVisibleSteps(selectedCoverages);
  const idx = flow.findIndex((s) => s.id === currentStepId);
  return flow[idx + 1];
}

export function getPrevStep(currentStepId: StepId, selectedCoverages: AllCoverageType[]): FormStep | undefined {
  const flow = getVisibleSteps(selectedCoverages);
  const idx = flow.findIndex((s) => s.id === currentStepId);
  if (idx > 0) return flow[idx - 1];
  return undefined;
}

export function getStepStatus(
  step: FormStep,
  completedStepIds: StepId[],
  currentStepId: StepId,
): FormStepStatus {
  if (step.id === currentStepId) return 'current';
  if (completedStepIds.includes(step.id)) return 'completed';
  return 'pending';
}

export function getStepIdFromPathname(pathname: string): StepId | undefined {
  const normalizedPath = pathname.replace(/\/quote\/[A-Z0-9-]+\//, '/quote/:quoteNumber/');
  return StepByPath.get(normalizedPath)?.id;
}

export function getStepBySlug(slug: string): FormStep | undefined {
  return FormFlow.find((s) => s.coverageSlug === slug);
}
