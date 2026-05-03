export const TRUDY_FIELD_MAP: Record<string, string> = {
  // Company info
  company_name: "company_name",
  entity_legal_name: "company_name",
  legal_name: "company_name",
  dba_name: "dba_name",
  dba: "dba_name",
  ein: "ein",
  fein: "ein",
  annual_revenue: "annual_revenue",
  revenue: "annual_revenue",
  total_employees: "total_employees",
  employees_total: "total_employees",
  num_employees: "total_employees",
  annual_payroll: "annual_payroll",
  payroll: "annual_payroll",
  // Address
  street_address: "street_address",
  address: "street_address",
  city: "city",
  state: "state",
  zip_code: "zip_code",
  zip: "zip_code",
  // Coverage
  coverage_types: "coverage_types",
  policy_type: "coverage_types",
  desired_limit: "limit",
  total_limit_requested: "limit",
  existing_insurance: "existing_insurance",
  existing_policies: "existing_insurance",
  prior_incidents: "prior_incidents",
  cyber_incidents: "prior_incidents",
  // Contact
  first_name: "first_name",
  last_name: "last_name",
  email: "email",
};

export function mapExtractedFields(
  extracted: Record<string, unknown>
): Record<string, unknown> {
  const result: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(extracted)) {
    const mapped = TRUDY_FIELD_MAP[key];
    if (mapped && value !== null && value !== undefined) {
      result[mapped] = value;
    }
  }
  return result;
}
