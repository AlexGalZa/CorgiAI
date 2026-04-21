// ─── API Response wrapper ───
export interface APIResponse<T = unknown> {
  success: boolean;
  message: string;
  data: T;
}

// ─── Policy ───
export interface PolicyData {
  label: string;
  coverage: string;
  effective: string;
  perOccurrence: string;
  aggregate: string;
  status: 'active' | 'expired' | 'pending';
}

/** Policy as returned from the API (GET /api/v1/policies/me) */
export interface APIPolicy {
  id: number;
  policy_number: string;
  coverage_type: string;
  coverage_slug: string;
  carrier: string;
  status: string;
  effective_date: string;
  expiration_date: string;
  premium: number;
  monthly_premium: number | null;
  billing_frequency: string;
  per_occurrence_limit: number | null;
  aggregate_limit: number | null;
  retention: number | null;
  coi_number: string | null;
  document_url: string | null;
  company_name: string | null;
  created_at: string;
}

// ─── Certificate ───
export interface CertParty {
  name: string;
  name2: string;
  street: string;
  city: string;
  state: string;
  zip: string;
  designations: DesignationType[];
}

export type DesignationType = 'ai' | 'lp' | 'ch';

/** Local-only certificate (used in the multi-step form before submission) */
export interface Certificate {
  id: string;
  policy: string;
  coverage: string;
  parties: CertParty[];
  date: string;
}

/** Certificate returned from the API */
export interface APICertificate {
  id: number;
  coi_number: string;
  custom_coi_number: string;
  holder_name: string;
  holder_second_line: string;
  holder_street_address: string;
  holder_suite: string;
  holder_city: string;
  holder_state: string;
  holder_zip: string;
  holder_full_address: string;
  is_additional_insured: boolean;
  endorsements: string[];
  service_location_job: string;
  service_location_address: string;
  service_you_provide_job: string;
  service_you_provide_service: string;
  status: 'active' | 'revoked' | 'expired';
  document_url: string | null;
  created_at: string;
  revoked_at: string | null;
}

export interface CertificateListResponse {
  certificates: APICertificate[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface AvailableCOI {
  coi_number: string;
  effective_date: string;
  expiration_date: string;
  custom_certificates_count: number;
}

export type CertStep = 'landing' | 'step1' | 'step2' | 'step3' | 'done';

// ─── Claims ───
export interface Claim {
  id: string;
  policyNum: string;
  coverage: string;
  date: string;
  status: 'Open' | 'In Progress' | 'Closed';
  description: string;
}

/** Claim as returned from the API list (GET /api/v1/claims/me) */
export interface APIClaimListItem {
  id: number;
  claim_number: string;
  policy_number: string;
  status: string;
  description: string;
  created_at: string;
  incident_date: string | null;
  loss_amount_estimate: number | null;
}

/** Claim document from the API */
export interface APIClaimDocument {
  id: number;
  file_type: string;
  original_filename: string;
  file_size: number;
  mime_type: string;
  created_at: string;
}

/** Full claim detail from the API (GET /api/v1/claims/{claim_number}) */
export interface APIClaimDetail {
  id: number;
  claim_number: string;
  policy_number: string;
  organization_name: string;
  first_name: string;
  last_name: string;
  email: string;
  phone_number: string;
  description: string;
  status: string;
  documents: APIClaimDocument[];
  created_at: string;
  updated_at: string;
}

export type ClaimsStep = 'landing' | 'form' | 'done';

// ─── Documents ───
export interface Document {
  id: string;
  name: string;
  type: 'policy' | 'certificate' | 'endorsement' | 'invoice';
  date: string;
  size: string;
  policyNum: string;
}

/** Document as returned from the API (GET /api/v1/users/documents) */
export interface APIDocument {
  id: number;
  category: string;
  title: string;
  policy_numbers: string[];
  effective_date: string | null;
  expiration_date: string | null;
  original_filename: string;
  file_size: number;
  created_at: string;
}

export interface APIDocumentsByCategory {
  policies: APIDocument[];
  certificates: APIDocument[];
  endorsements: APIDocument[];
  receipts: APIDocument[];
  loss_runs: APIDocument[];
}

// ─── Billing ───
export interface BillingPlanItem {
  name: string;
  sub: string;
  amount: string;
  per: string;
}

export interface BillingHistoryItem {
  name: string;
  sub: string;
  date: string;
  amount: string;
  status: 'upcoming' | 'paid';
  invoiceId: string;
  policies: string;
  period: string;
  due: string;
  method: string;
  breakdown: { label: string; amount: string }[];
  total: string;
}

/** Billing info from the API (GET /api/v1/policies/billing) */
export interface APIBillingInfo {
  has_billing: boolean;
  payment_method: {
    brand: string;
    last4: string;
    exp_month: number;
    exp_year: number;
  } | null;
  plans: APIBillingPlan[];
  history: APIPaymentHistory[];
}

export interface APIBillingPlan {
  policy_number: string;
  coverage_type: string;
  billing_frequency: string;
  amount: number;
  next_payment_date: string | null;
  status: string;
}

export interface APIPaymentHistory {
  id: string;
  amount: number;
  currency: string;
  status: string;
  description: string;
  created_at: string;
  invoice_url: string | null;
}

// ─── Quotes ───
export type QuoteStep = 'landing' | 'step1' | 'step2' | 'step3' | 'step4' | 'step5';

export interface QuoteType {
  id: string;
  name: string;
  desc: string;
}

export interface AvailableCoverage {
  name: string;
  desc: string;
}

/** Quote as returned from the API list (GET /api/v1/quotes/me) */
export interface APIQuoteListItem {
  id: number;
  quote_number: string;
  status: string;
  coverages: string[];
  quote_amount: number | null;
  created_at: string;
}

/** Full quote detail from the API (GET /api/v1/quotes/{quote_number}) */
export interface APIQuoteDetail {
  id: number;
  quote_number: string;
  status: string;
  coverages: string[];
  created_at: string;
  quote_amount: number | null;
  monthly_amount: number | null;
  custom_products: APICustomProduct[];
  custom_products_total: number;
  custom_products_monthly: number;
  total_amount: number;
  total_monthly: number;
  needs_review: boolean;
  rating_result: APIRatingResult | null;
}

export interface APICustomProduct {
  id: string;
  name: string;
  product_type: string;
  per_occurrence_limit: number | null;
  aggregate_limit: number | null;
  retention: number | null;
  price: number;
}

export interface APIRatingResult {
  success: boolean;
  total_premium: number | null;
  breakdown: Record<string, { premium: number; breakdown: string }> | null;
  review_reasons: { coverage: string; reason: string }[] | null;
}

// ─── Organization ───
export interface OrgMember {
  name: string;
  email: string;
  role: 'Owner' | 'Admin' | 'Member';
  initials: string;
  color: string;
}

/** Organization member from the API */
export interface APIOrgMember {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
  joined_at: string;
}

/** Organization invite from the API */
export interface APIOrgInvite {
  id: number;
  code: string;
  default_role: string;
  max_uses: number | null;
  use_count: number;
  expires_at: string | null;
  is_valid: boolean;
  created_at: string;
}

/** Organization detail from the API (GET /api/v1/organizations/me) */
export interface APIOrgDetail {
  id: number;
  name: string;
  role: string;
  is_personal: boolean;
  members: APIOrgMember[];
  invites: APIOrgInvite[];
}

// ─── User ───
export interface APIUser {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  phone_number: string;
  company_name: string;
  created_at: string;
  is_impersonated: boolean;
  organizations: {
    id: number;
    name: string;
    role: string;
    is_personal: boolean;
  }[];
}

// ─── Auth ───
export interface LoginPayload {
  email: string;
}

export interface VerifyOtpPayload {
  email: string;
  code: string;
}

export interface RegisterPayload {
  company: string;
  firstName: string;
  lastName: string;
  email: string;
}

// ─── Navigation ───
export type TabName =
  | 'coverage'
  | 'certificates'
  | 'claims'
  | 'documents'
  | 'billing'
  | 'quotes'
  | 'organization';
