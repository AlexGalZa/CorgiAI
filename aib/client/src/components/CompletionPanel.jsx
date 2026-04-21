import React from 'react';

function boolDisplay(val) {
  if (val === true) return 'Yes';
  if (val === false) return 'No';
  return null;
}

export default function CompletionPanel({ intake, onNewChat }) {
  if (!intake) return null;

  const sections = [
    {
      title: 'Business',
      fields: [
        { label: 'Company Name', value: intake.company_name },
        { label: 'DBA', value: intake.dba },
        { label: 'Address', value: intake.address },
        { label: 'FEIN', value: intake.fein },
        { label: 'Business Description', value: intake.business_description },
        { label: 'Years in Business', value: intake.years_in_business },
      ],
    },
    {
      title: 'Financials & Workforce',
      fields: [
        { label: 'Annual Revenue', value: intake.annual_revenue },
        { label: 'Total Employees', value: intake.employees_total },
        { label: 'FT/PT Breakdown', value: intake.employees_ft_pt },
        { label: 'Annual Payroll', value: intake.annual_payroll },
      ],
    },
    {
      title: 'Coverage',
      fields: [
        { label: 'Policy Type', value: intake.policy_type },
        { label: 'Coverage Limit', value: intake.total_limit_requested },
        { label: 'Desired Effective Date', value: intake.desired_effective_date },
        { label: 'Existing Policies', value: intake.existing_policies },
        { label: 'Prior Carrier', value: intake.prior_carrier },
        { label: 'Retroactive Date', value: intake.retroactive_date },
      ],
    },
    {
      title: 'Claims History',
      fields: [
        { label: 'Claims History', value: intake.claims_history },
        { label: 'Prior Cyber Incidents', value: intake.cyber_incidents },
        { label: 'Prior EPL Claims', value: intake.epl_claims },
      ],
    },
    {
      title: 'Cyber Security',
      fields: [
        { label: 'Records Held', value: intake.records_count },
        { label: 'MFA Enabled', value: boolDisplay(intake.cyber_mfa) },
        { label: 'Regular Backups', value: boolDisplay(intake.cyber_backups) },
        { label: 'Endpoint Security', value: boolDisplay(intake.cyber_endpoint_security) },
      ],
    },
    {
      title: 'Policy-Specific',
      fields: [
        { label: 'Shareholders 5%+', value: intake.shareholders_5pct },
        { label: 'FYE Financials', value: intake.fye_financials },
        { label: 'Last 12mo Revenue', value: intake.last_12mo_revenue },
        { label: 'International Entities', value: intake.epl_international_entities },
        { label: 'ERISA Plan Assets', value: intake.erisa_plan_assets },
        { label: 'Media Content Type', value: intake.media_content_type },
      ],
    },
    {
      title: 'Other',
      fields: [
        { label: 'Additional Notes', value: intake.additional_notes },
      ],
    },
  ];

  return (
    <div className="completion-panel">
      <div className="completion-header">
        <div className="completion-icon">✅</div>
        <h2 className="completion-title">Intake Complete</h2>
        <p className="completion-subtitle">
          Here's a summary of the information collected. Your broker will review this and prepare quotes.
        </p>
      </div>

      {sections.map((section) => {
        const visibleFields = section.fields.filter(f => f.value != null && f.value !== '');
        if (visibleFields.length === 0) return null;
        return (
          <div key={section.title} className="completion-section">
            <h3 className="completion-section-title">{section.title}</h3>
            <div className="completion-fields">
              {visibleFields.map((field, i) => (
                <div key={i} className="completion-field">
                  <span className="completion-field-label">{field.label}</span>
                  <span className="completion-field-value">{field.value}</span>
                </div>
              ))}
            </div>
          </div>
        );
      })}

      {intake.client_questions_flagged && intake.client_questions_flagged.length > 0 && (
        <div className="completion-section">
          <h3 className="completion-section-title">Questions for Broker Follow-up</h3>
          <ul>
            {intake.client_questions_flagged.map((q, i) => (
              <li key={i}>{q}</li>
            ))}
          </ul>
        </div>
      )}

      <button className="completion-new-chat" onClick={onNewChat}>
        Start New Intake
      </button>
    </div>
  );
}
