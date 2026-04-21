"""
Extraction prompt — runs on completed conversations to pull structured data.
"""

EXTRACTION_PROMPT = """You are a data extraction assistant. Given the following conversation transcript between an insurance broker AI named Trudy at Corgi Insurance and a client, extract all relevant insurance intake information into a structured JSON object.

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
  "policy_type": "Type(s) of insurance requested (Cyber, D&O, EPL, ERISA, Media)",
  "total_limit_requested": "Desired coverage limit",
  "existing_policies": "Description of any existing insurance policies",
  "financials_available": "Whether financial documents are available",
  "records_count": "Number of records held (for cyber)",
  "cyber_incidents": "Description of any prior cyber incidents",
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
- For boolean fields, use true/false
- For array fields, use [] if empty
- client_questions_flagged should contain any questions the client asked that need broker follow-up
- additional_notes should capture anything important that doesn't fit other fields

CONVERSATION TRANSCRIPT:
"""
