const db = require('../config/database');
const anthropic = require('./anthropic');
const EXTRACTION_PROMPT = require('../prompts/extraction');

async function extractIntakeData(sessionId) {
  const messagesResult = await db.query(
    `SELECT role, content, attachments FROM messages WHERE session_id = $1 ORDER BY created_at ASC`,
    [sessionId]
  );

  if (messagesResult.rows.length === 0) {
    throw new Error('No messages found for session');
  }

  const transcript = messagesResult.rows
    .map(m => {
      let line = `${m.role.toUpperCase()}: ${m.content}`;
      const attachments = typeof m.attachments === 'string'
        ? JSON.parse(m.attachments)
        : m.attachments;
      if (attachments && attachments.length > 0) {
        const fileList = attachments.map(a => `${a.filename} (${a.type})`).join(', ');
        line += `\n[Attachments: ${fileList}]`;
      }
      return line;
    })
    .join('\n\n');

  const fullPrompt = EXTRACTION_PROMPT + transcript;
  const extracted = await anthropic.extract(fullPrompt);
  const intake = await storeIntake(sessionId, extracted);
  return intake;
}

async function storeIntake(sessionId, data) {
  const result = await db.query(
    `INSERT INTO intakes (
      session_id, company_name, dba, address, fein,
      business_description, annual_revenue, employees_total,
      employees_ft_pt, annual_payroll, years_in_business,
      prior_carrier, retroactive_date, desired_effective_date,
      policy_type, total_limit_requested, existing_policies,
      financials_available, claims_history, records_count,
      cyber_incidents, cyber_mfa, cyber_backups, cyber_endpoint_security,
      shareholders_5pct, fye_financials, last_12mo_revenue,
      epl_international_entities, epl_claims, erisa_plan_assets,
      media_content_type, contract_required, contract_provided,
      uploaded_documents, client_questions_flagged, additional_notes, raw_extraction
    ) VALUES (
      $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
      $11, $12, $13, $14, $15, $16, $17, $18, $19, $20,
      $21, $22, $23, $24, $25, $26, $27, $28, $29, $30,
      $31, $32, $33, $34, $35, $36, $37
    )
    ON CONFLICT (session_id) DO UPDATE SET
      company_name = EXCLUDED.company_name,
      dba = EXCLUDED.dba,
      address = EXCLUDED.address,
      fein = EXCLUDED.fein,
      business_description = EXCLUDED.business_description,
      annual_revenue = EXCLUDED.annual_revenue,
      employees_total = EXCLUDED.employees_total,
      employees_ft_pt = EXCLUDED.employees_ft_pt,
      annual_payroll = EXCLUDED.annual_payroll,
      years_in_business = EXCLUDED.years_in_business,
      prior_carrier = EXCLUDED.prior_carrier,
      retroactive_date = EXCLUDED.retroactive_date,
      desired_effective_date = EXCLUDED.desired_effective_date,
      policy_type = EXCLUDED.policy_type,
      total_limit_requested = EXCLUDED.total_limit_requested,
      existing_policies = EXCLUDED.existing_policies,
      financials_available = EXCLUDED.financials_available,
      claims_history = EXCLUDED.claims_history,
      records_count = EXCLUDED.records_count,
      cyber_incidents = EXCLUDED.cyber_incidents,
      cyber_mfa = EXCLUDED.cyber_mfa,
      cyber_backups = EXCLUDED.cyber_backups,
      cyber_endpoint_security = EXCLUDED.cyber_endpoint_security,
      shareholders_5pct = EXCLUDED.shareholders_5pct,
      fye_financials = EXCLUDED.fye_financials,
      last_12mo_revenue = EXCLUDED.last_12mo_revenue,
      epl_international_entities = EXCLUDED.epl_international_entities,
      epl_claims = EXCLUDED.epl_claims,
      erisa_plan_assets = EXCLUDED.erisa_plan_assets,
      media_content_type = EXCLUDED.media_content_type,
      contract_required = EXCLUDED.contract_required,
      contract_provided = EXCLUDED.contract_provided,
      uploaded_documents = EXCLUDED.uploaded_documents,
      client_questions_flagged = EXCLUDED.client_questions_flagged,
      additional_notes = EXCLUDED.additional_notes,
      raw_extraction = EXCLUDED.raw_extraction
    RETURNING *`,
    [
      sessionId,
      data.company_name || null,
      data.dba || null,
      data.address || null,
      data.fein || null,
      data.business_description || null,
      data.annual_revenue || null,
      data.employees_total || null,
      data.employees_ft_pt || null,
      data.annual_payroll || null,
      data.years_in_business || null,
      data.prior_carrier || null,
      data.retroactive_date || null,
      data.desired_effective_date || null,
      data.policy_type || null,
      data.total_limit_requested || null,
      data.existing_policies || null,
      data.financials_available || null,
      data.claims_history || null,
      data.records_count || null,
      data.cyber_incidents || null,
      data.cyber_mfa ?? null,
      data.cyber_backups ?? null,
      data.cyber_endpoint_security ?? null,
      data.shareholders_5pct || null,
      data.fye_financials || null,
      data.last_12mo_revenue || null,
      data.epl_international_entities || null,
      data.epl_claims || null,
      data.erisa_plan_assets || null,
      data.media_content_type || null,
      data.contract_required || false,
      data.contract_provided || false,
      JSON.stringify(data.uploaded_documents || []),
      JSON.stringify(data.client_questions_flagged || []),
      data.additional_notes || null,
      JSON.stringify(data),
    ]
  );

  return result.rows[0];
}

async function getIntake(sessionId) {
  const result = await db.query(
    `SELECT * FROM intakes WHERE session_id = $1`,
    [sessionId]
  );
  return result.rows[0] || null;
}

async function listIntakes() {
  const result = await db.query(
    `SELECT i.*, s.status as session_status, s.created_at as session_created_at
     FROM intakes i
     JOIN sessions s ON s.id = i.session_id
     ORDER BY i.created_at DESC`
  );
  return result.rows;
}

module.exports = { extractIntakeData, getIntake, listIntakes };
