/**
 * Extraction prompt — runs on completed conversations to pull structured data
 */

const EXTRACTION_PROMPT = `You are a data extraction assistant. Given the following conversation transcript between an AI insurance advisor and a client, extract all relevant insurance intake information into a structured JSON object.

Extract ONLY information that was explicitly stated or clearly implied in the conversation. Use null for any field where information was not provided.

Return a JSON object with exactly these fields:

{
  "company_name": "Legal company name",
  "dba": "Doing business as name, if different",
  "address": "Full business address",
  "fein": "Federal Employer Identification Number",
  "business_description": "Brief description of what the business does",
  "annual_revenue": "Annual revenue figure",
  "employees_total": "Total number of employees",
  "employees_ft_pt": "Breakdown of full-time vs part-time",
  "annual_payroll": "Annual payroll amount",
  "years_in_business": "How long the company has been in business",
  "prior_carrier": "Current or prior insurance carrier name",
  "retroactive_date": "Retroactive date on existing policy, if renewing",
  "desired_effective_date": "Desired policy start/effective date",
  "policy_type": "Type(s) of insurance requested (Cyber, D&O, EPL, ERISA, Media)",
  "total_limit_requested": "Desired coverage limit",
  "existing_policies": "Description of any existing insurance policies",
  "financials_available": "Whether financial documents are available",
  "claims_history": "General description of any claims or incidents in the past 3 years across all lines",
  "records_count": "Number of records held (for cyber)",
  "cyber_incidents": "Description of any prior cyber incidents",
  "cyber_mfa": null,
  "cyber_backups": null,
  "cyber_endpoint_security": null,
  "shareholders_5pct": "Shareholders owning 5% or more (for D&O)",
  "fye_financials": "Fiscal year-end financial information (for D&O)",
  "last_12mo_revenue": "Last 12 months revenue (for D&O)",
  "epl_international_entities": "International entities (for EPL)",
  "epl_claims": "Prior EPL claims",
  "erisa_plan_assets": "Plan assets under management (for ERISA)",
  "media_content_type": "Type of media content produced (for Media)",
  "contract_required": false,
  "contract_provided": false,
  "uploaded_documents": [],
  "client_questions_flagged": [],
  "additional_notes": "Any other relevant information or special requests"
}

Important:
- Return ONLY valid JSON, no markdown code fences, no explanation
- Use null for missing fields, not empty strings
- For boolean fields (cyber_mfa, cyber_backups, cyber_endpoint_security, contract_required, contract_provided), use true/false or null if not discussed
- For array fields, use [] if empty
- client_questions_flagged should contain any questions the client asked that need broker follow-up
- additional_notes should capture anything important that doesn't fit other fields

CONVERSATION TRANSCRIPT:
`;

module.exports = EXTRACTION_PROMPT;
