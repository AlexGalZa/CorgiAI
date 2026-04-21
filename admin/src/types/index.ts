// ─── User ────────────────────────────────────────────────────────────────────

export interface User {
  id: number
  email: string
  first_name: string
  last_name: string
  role: 'bdr' | 'ae' | 'ae_underwriting' | 'finance' | 'broker' | 'admin' | 'claims_adjuster' | 'customer_support' | 'policyholder'
  full_name: string
  phone_number: string
  company_name: string
  is_active: boolean
  is_staff: boolean
  created_at: string
  updated_at: string
}

// ─── Organization ────────────────────────────────────────────────────────────

export interface Organization {
  id: number
  name: string
  owner: number
  is_personal: boolean
  created_at: string
  updated_at: string
}

// ─── Brokered Quote Request ──────────────────────────────────────────────────

export interface BrokeredQuoteRequest {
  id: number
  company_name: string
  status: string
  status_display: string
  coverage_types: string[]
  coverage_type_display: string
  carrier: string
  carrier_display: string
  requested_coverage_detail: string
  aggregate_limit: string
  per_occurrence_limit: string
  retention: string
  additional_notes: string
  blocker_type: string
  blocker_detail: string
  requester: number | null
  requester_name: string
  requester_email: string
  quote: number | null
  quote_document_url: string
  quote_document_secondary_url: string
  premium_amount: string | null
  django_admin_url: string
  is_bound: boolean
  custom_product_created: boolean
  docs_uploaded: boolean
  missing_docs_note: string
  stripe_confirmed: boolean
  coi_document_url: string
  client_contact_url: string
  client_email: string
  notes: string
  decline_reason: string
  airtable_id: number | null
  run_id: string
  has_blocker: boolean
  fulfillment_complete: boolean
  created_at: string
  updated_at: string
}

// ─── Quote ───────────────────────────────────────────────────────────────────

export interface Quote {
  id: number
  quote_number: string
  company: number
  company_detail: { id: number; entity_legal_name: string }
  user: number
  organization: number | null
  status: string
  quote_amount: string
  quoted_at: string | null
  billing_frequency: string
  current_step: string
  coverages: Record<string, unknown> | null
  coverage_data: Record<string, unknown> | null
  limits_retentions: Record<string, unknown> | null
  rating_result: Record<string, unknown> | null
  form_data_snapshot: Record<string, unknown> | null
  referral_partner: string
  promo_code: string
  created_at: string
  updated_at: string
}

// ─── Policy ──────────────────────────────────────────────────────────────────

export interface Policy {
  id: number
  policy_number: string
  quote: number | null
  coverage_type: string
  carrier: string
  is_brokered: boolean
  premium: string
  monthly_premium: string
  billing_frequency: string
  limits_retentions: Record<string, unknown> | null
  coi_number: string
  insured_fein: string
  purchased_at: string | null
  paid_to_date: string | null
  effective_date: string | null
  expiration_date: string | null
  status: string
  insured_legal_name: string
  principal_state: string
  transaction_count: number
  created_at: string
  updated_at: string
}

// ─── Claim ───────────────────────────────────────────────────────────────────

export interface Claim {
  id: number
  claim_number: string
  policy: number
  user: number
  organization: number | null
  organization_name: string
  first_name: string
  last_name: string
  email: string
  phone_number: string
  description: string
  status: string
  admin_notes: string
  loss_state: string
  paid_loss: string
  paid_lae: string
  case_reserve_loss: string
  case_reserve_lae: string
  total_incurred: string
  claim_report_date: string | null
  created_at: string
  updated_at: string
}

// ─── Internal Document ───────────────────────────────────────────────────────

export interface InternalDocument {
  id: number
  claim: number
  claim_number: string
  policy: number | null
  document_type: string
  status: string
  original_filename: string
  s3_key: string
  s3_url: string
  generated_at: string | null
  reviewed_by: string
  reviewed_at: string | null
  sent_at: string | null
  notes: string
  created_at: string
  updated_at: string
}

// ─── Payment Summary ─────────────────────────────────────────────────────────

export interface PaymentSummary {
  total_paid: number
  total_pending: number
  total_failed: number
  total_refunded: number
  paid_count: number
  pending_count: number
  failed_count: number
}

// ─── Payment ─────────────────────────────────────────────────────────────────

export interface Payment {
  id: number
  policy: number
  stripe_invoice_id: string
  amount: string
  status: string
  paid_at: string | null
  created_at: string
  updated_at: string
}

// ─── Producer ────────────────────────────────────────────────────────────────

export interface Producer {
  id: number
  name: string
  producer_type: string
  email: string
  license_number: string
  is_active: boolean
  created_at: string
  updated_at: string
}

// ─── Certificate ─────────────────────────────────────────────────────────────

export interface Certificate {
  id: number
  user: number
  organization: number | null
  coi_number: string
  custom_coi_number: string
  holder_name: string
  holder_city: string
  holder_state: string
  is_additional_insured: boolean
  created_at: string
  updated_at: string
}

// ─── Paginated Response ──────────────────────────────────────────────────────

export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

// ─── Analytics ───────────────────────────────────────────────────────────────

export interface PipelineStatusCount {
  status: string
  count: number
}

export interface PremiumByCarrier {
  carrier: string
  total_premium: number
}

export interface CoverageBreakdown {
  coverage_type_display: string
  count: number
}

export interface PolicyStats {
  active_count: number
  total_premium: number
}

export interface ClaimsSummary {
  by_status: Array<{ status: string; count: number }>
  total_case_reserve_loss: number
  total_case_reserve_lae: number
  total_paid_loss: number
  total_paid_lae: number
  total_reserves: number
}

export interface RequesterStat {
  requester: number
  email: string
  first_name: string
  last_name: string
  request_count: number
  total_premium: number
  quoted_count: number
  bound_count: number
  bind_rate: number
}

export interface ActionItems {
  blocked_requests: number
  unreviewed_documents: number
  expiring_policies_30d: number
  pending_claims: number
}

export interface MonthlyPremium {
  month: string
  premium: number
}

export interface LossRatio {
  total_paid_losses: number
  total_paid_lae: number
  total_earned_premium: number
  loss_ratio: number
}

// ─── Audit Log ───────────────────────────────────────────────────────────────

export interface AuditEntry {
  id: number
  user_email: string
  user_name: string
  action: string
  entity_type: string
  entity_id: number
  entity_name: string
  field_changed: string
  old_value: string
  new_value: string
  timestamp: string
}
