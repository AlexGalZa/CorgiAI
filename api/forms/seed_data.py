"""
Seed data for all 8 Tier 1 coverage type form definitions.

Each form mirrors the questionnaire fields used by the rating engine,
with realistic labels, help text, conditional logic, and rating field
mappings so the frontend can render them dynamically.
"""

from __future__ import annotations

# ═════════════════════════════════════════════════════════════════════
# 1. Commercial General Liability
# ═════════════════════════════════════════════════════════════════════

CGL_FORM = {
    "name": "Commercial General Liability Questionnaire",
    "slug": "cgl-questionnaire",
    "version": 1,
    "description": "Dynamic questionnaire for CGL coverage rating.",
    "coverage_type": "commercial-general-liability",
    "is_active": True,
    "fields": [
        {
            "key": "primary_operations_hazard",
            "label": "Primary Operations Hazard Level",
            "field_type": "select",
            "required": True,
            "help_text": "Select the hazard level that best describes your primary business operations.",
            "options": [
                {"value": "low-hazard", "label": "Low Hazard"},
                {"value": "moderate-hazard", "label": "Moderate Hazard"},
                {"value": "elevated-hazard", "label": "Elevated Hazard"},
                {"value": "high-hazard", "label": "High Hazard"},
            ],
            "order": 1,
            "group": "operations",
        },
        {
            "key": "is_address_primary_office",
            "label": "Is your business address your primary office?",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 2,
            "group": "operations",
        },
        {
            "key": "office_square_footage",
            "label": "Office Square Footage",
            "field_type": "select",
            "required": True,
            "options": [
                {"value": "up_to_2500", "label": "Up to 2,500 sq ft"},
                {"value": "2501_5000", "label": "2,501 - 5,000 sq ft"},
                {"value": "5001_10000", "label": "5,001 - 10,000 sq ft"},
                {"value": "10001_25000", "label": "10,001 - 25,000 sq ft"},
                {"value": "over_25000", "label": "Over 25,000 sq ft"},
                {"value": "not_applicable", "label": "Not Applicable"},
            ],
            "order": 3,
            "group": "operations",
        },
        {
            "key": "has_contractual_liability",
            "label": "Do you assume contractual liability under agreements?",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 4,
            "group": "liability",
        },
        {
            "key": "has_other_exposures",
            "label": "Are there other exposure risks beyond your primary operations?",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 5,
            "group": "liability",
        },
        {
            "key": "other_exposures_description",
            "label": "Describe other exposures",
            "field_type": "textarea",
            "required": True,
            "placeholder": "Describe any additional exposure risks...",
            "order": 6,
            "group": "liability",
            "validation": {"max_length": 2000},
        },
        {
            "key": "has_physical_locations",
            "label": "Do you have physical locations beyond your primary office?",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 7,
            "group": "premises",
        },
        {
            "key": "physical_locations_description",
            "label": "Describe physical locations",
            "field_type": "textarea",
            "placeholder": "List locations, square footage, and use...",
            "order": 8,
            "group": "premises",
            "validation": {"max_length": 2000},
        },
        {
            "key": "has_safety_measures",
            "label": "Do you have safety measures in place?",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": "Yes", "label": "Yes"},
                {"value": "No", "label": "No"},
                {"value": "N/A", "label": "N/A"},
            ],
            "order": 9,
            "group": "premises",
        },
        {
            "key": "has_hazardous_materials",
            "label": "Do you use or store hazardous materials?",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 10,
            "group": "premises",
        },
        {
            "key": "hazardous_materials_description",
            "label": "Describe hazardous materials",
            "field_type": "textarea",
            "placeholder": "Describe materials, storage, and safety protocols...",
            "order": 11,
            "group": "premises",
            "validation": {"max_length": 2000},
        },
        {
            "key": "has_products_completed_operations",
            "label": "Do you have products or completed operations exposure?",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 12,
            "group": "products",
        },
        {
            "key": "products_completed_operations_description",
            "label": "Describe products/completed operations",
            "field_type": "textarea",
            "placeholder": "Describe your products or completed operations...",
            "order": 13,
            "group": "products",
            "validation": {"max_length": 2000},
        },
        {
            "key": "uses_subcontractors",
            "label": "Do you use subcontractors?",
            "field_type": "radio",
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 14,
            "group": "products",
        },
        {
            "key": "requires_subcontractor_insurance",
            "label": "Do you require subcontractors to carry their own insurance?",
            "field_type": "radio",
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 15,
            "group": "products",
        },
    ],
    "conditional_logic": {
        "rules": [
            {
                "target_field": "other_exposures_description",
                "action": "show",
                "conditions": [
                    {
                        "field_key": "has_other_exposures",
                        "operator": "equals",
                        "value": True,
                    }
                ],
                "match": "all",
            },
            {
                "target_field": "physical_locations_description",
                "action": "show",
                "conditions": [
                    {
                        "field_key": "has_physical_locations",
                        "operator": "equals",
                        "value": True,
                    }
                ],
                "match": "all",
            },
            {
                "target_field": "hazardous_materials_description",
                "action": "show",
                "conditions": [
                    {
                        "field_key": "has_hazardous_materials",
                        "operator": "equals",
                        "value": True,
                    }
                ],
                "match": "all",
            },
            {
                "target_field": "products_completed_operations_description",
                "action": "show",
                "conditions": [
                    {
                        "field_key": "has_products_completed_operations",
                        "operator": "equals",
                        "value": True,
                    }
                ],
                "match": "all",
            },
            {
                "target_field": "requires_subcontractor_insurance",
                "action": "show",
                "conditions": [
                    {
                        "field_key": "uses_subcontractors",
                        "operator": "equals",
                        "value": True,
                    }
                ],
                "match": "all",
            },
        ]
    },
    "rating_field_mappings": {
        "primary_operations_hazard": "primary_operations_hazard",
        "is_address_primary_office": "is_address_primary_office",
        "office_square_footage": "office_square_footage",
        "has_contractual_liability": "has_contractual_liability",
        "has_other_exposures": "has_other_exposures",
        "other_exposures_description": "other_exposures_description",
        "has_physical_locations": "has_physical_locations",
        "physical_locations_description": "physical_locations_description",
        "has_safety_measures": "has_safety_measures",
        "has_hazardous_materials": "has_hazardous_materials",
        "has_products_completed_operations": "has_products_completed_operations",
        "products_completed_operations_description": "products_completed_operations_description",
        "uses_subcontractors": "uses_subcontractors",
        "requires_subcontractor_insurance": "requires_subcontractor_insurance",
    },
}


# ═════════════════════════════════════════════════════════════════════
# 2. Directors & Officers
# ═════════════════════════════════════════════════════════════════════

DO_FORM = {
    "name": "Directors & Officers Questionnaire",
    "slug": "do-questionnaire",
    "version": 1,
    "description": "Dynamic questionnaire for D&O coverage rating.",
    "coverage_type": "directors-and-officers",
    "is_active": True,
    "fields": [
        {
            "key": "is_publicly_traded",
            "label": "Is your company publicly traded?",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 1,
            "group": "corporate_structure",
        },
        {
            "key": "public_offering_details",
            "label": "Public offering details",
            "field_type": "textarea",
            "placeholder": "Describe stock exchange, ticker, market cap...",
            "order": 2,
            "group": "corporate_structure",
            "validation": {"max_length": 2000},
        },
        {
            "key": "has_mergers_acquisitions",
            "label": "Any pending or recent mergers, acquisitions, or divestitures?",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 3,
            "group": "corporate_structure",
        },
        {
            "key": "mergers_acquisitions_details",
            "label": "M&A details",
            "field_type": "textarea",
            "placeholder": "Describe the transaction(s)...",
            "order": 4,
            "group": "corporate_structure",
            "validation": {"max_length": 2000},
        },
        {
            "key": "board_size",
            "label": "Total number of board members",
            "field_type": "number",
            "required": True,
            "placeholder": "e.g. 5",
            "validation": {"min": 1, "max": 50},
            "order": 5,
            "group": "board",
            "width": "half",
        },
        {
            "key": "independent_directors",
            "label": "Number of independent directors",
            "field_type": "number",
            "required": True,
            "placeholder": "e.g. 3",
            "validation": {"min": 0, "max": 50},
            "order": 6,
            "group": "board",
            "width": "half",
        },
        {
            "key": "director_names",
            "label": "Names of directors",
            "field_type": "textarea",
            "required": True,
            "placeholder": "Comma-separated list of director names",
            "order": 7,
            "group": "board",
        },
        {
            "key": "has_board_meetings",
            "label": "Does the board hold regular meetings?",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 8,
            "group": "board",
        },
        {
            "key": "funding_raised",
            "label": "Total funding raised",
            "field_type": "currency",
            "required": True,
            "placeholder": "e.g. 5000000",
            "help_text": "Total capital raised to date (USD).",
            "validation": {"min": 0},
            "order": 9,
            "group": "financials",
        },
        {
            "key": "funding_date",
            "label": "Date of last funding round",
            "field_type": "date",
            "order": 10,
            "group": "financials",
            "width": "half",
        },
        {
            "key": "has_financial_audits",
            "label": "Are annual financial audits conducted?",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 11,
            "group": "financials",
        },
        {
            "key": "has_legal_compliance_officer",
            "label": "Do you have a legal or compliance officer?",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 12,
            "group": "governance",
        },
        {
            "key": "is_profitable",
            "label": "Is the company currently profitable?",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 13,
            "group": "financials",
        },
        {
            "key": "has_indebtedness",
            "label": "Does the company have outstanding debt obligations?",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 14,
            "group": "financials",
        },
        {
            "key": "has_breached_loan_covenants",
            "label": "Has the company breached any loan covenants?",
            "field_type": "radio",
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 15,
            "group": "financials",
        },
    ],
    "conditional_logic": {
        "rules": [
            {
                "target_field": "public_offering_details",
                "action": "show",
                "conditions": [
                    {
                        "field_key": "is_publicly_traded",
                        "operator": "equals",
                        "value": True,
                    }
                ],
                "match": "all",
            },
            {
                "target_field": "mergers_acquisitions_details",
                "action": "show",
                "conditions": [
                    {
                        "field_key": "has_mergers_acquisitions",
                        "operator": "equals",
                        "value": True,
                    }
                ],
                "match": "all",
            },
            {
                "target_field": "has_breached_loan_covenants",
                "action": "show",
                "conditions": [
                    {
                        "field_key": "has_indebtedness",
                        "operator": "equals",
                        "value": True,
                    }
                ],
                "match": "all",
            },
        ]
    },
    "rating_field_mappings": {
        "is_publicly_traded": "is_publicly_traded",
        "has_mergers_acquisitions": "has_mergers_acquisitions",
        "board_size": "board_size",
        "independent_directors": "independent_directors",
        "director_names": "director_names",
        "has_board_meetings": "has_board_meetings",
        "funding_raised": "funding_raised",
        "funding_date": "funding_date",
        "has_financial_audits": "has_financial_audits",
        "has_legal_compliance_officer": "has_legal_compliance_officer",
        "is_profitable": "is_profitable",
        "has_indebtedness": "has_indebtedness",
        "has_breached_loan_covenants": "has_breached_loan_covenants",
    },
}


# ═════════════════════════════════════════════════════════════════════
# 3. Technology E&O
# ═════════════════════════════════════════════════════════════════════

TECH_EO_FORM = {
    "name": "Technology E&O Questionnaire",
    "slug": "tech-eo-questionnaire",
    "version": 1,
    "description": "Dynamic questionnaire for Technology E&O coverage rating.",
    "coverage_type": "technology-errors-and-omissions",
    "is_active": True,
    "fields": [
        {
            "key": "services_description",
            "label": "Describe the technology services you provide",
            "field_type": "textarea",
            "required": True,
            "placeholder": "e.g. SaaS platform for project management, API integrations...",
            "help_text": "This description is used to classify your hazard class for rating.",
            "validation": {"min_length": 20, "max_length": 3000},
            "order": 1,
            "group": "services",
        },
        {
            "key": "service_criticality",
            "label": "How critical are your services to your clients' operations?",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": "not-critical", "label": "Not Critical"},
                {"value": "moderately-critical", "label": "Moderately Critical"},
                {"value": "highly-critical", "label": "Highly Critical"},
            ],
            "order": 2,
            "group": "services",
        },
        {
            "key": "industry_hazards",
            "label": "Do you serve any of these regulated industries?",
            "field_type": "checkbox_group",
            "help_text": "Select all that apply.",
            "options": [
                {"value": "healthcare", "label": "Healthcare"},
                {"value": "fintech", "label": "Fintech / Financial Services"},
                {"value": "govtech", "label": "Government / GovTech"},
                {"value": "industrial", "label": "Industrial / IoT"},
                {"value": "none", "label": "None of the above"},
            ],
            "order": 3,
            "group": "services",
        },
        {
            "key": "has_liability_protections",
            "label": "Do you have contractual liability protections (limitation of liability clauses)?",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 4,
            "group": "risk_management",
        },
        {
            "key": "has_quality_assurance",
            "label": "Do you have formal QA processes?",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 5,
            "group": "risk_management",
        },
        {
            "key": "has_prior_incidents",
            "label": "Have you had any prior E&O claims or incidents?",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 6,
            "group": "claims_history",
        },
        {
            "key": "incident_details",
            "label": "Describe prior incidents",
            "field_type": "textarea",
            "placeholder": "Describe the incidents, dates, and outcomes...",
            "order": 7,
            "group": "claims_history",
            "validation": {"max_length": 3000},
        },
        {
            "key": "uses_ai",
            "label": "Do your services use or incorporate AI/ML?",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 8,
            "group": "ai_coverage",
        },
        {
            "key": "wants_ai_coverage",
            "label": "Would you like to add AI liability coverage?",
            "field_type": "radio",
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 9,
            "group": "ai_coverage",
        },
        {
            "key": "ai_coverage_options",
            "label": "Select AI coverage endorsements",
            "field_type": "checkbox_group",
            "help_text": "Choose which AI-specific coverages to include.",
            "options": [
                {
                    "value": "algorithmic-bias-liability",
                    "label": "Algorithmic Bias Liability",
                },
                {
                    "value": "ai-intellectual-property-liability",
                    "label": "AI Intellectual Property Liability",
                },
                {
                    "value": "regulatory-investigation-defense-costs",
                    "label": "Regulatory Investigation Defense Costs",
                },
                {
                    "value": "hallucination-defamation-liability",
                    "label": "Hallucination & Defamation Liability",
                },
                {
                    "value": "training-data-misuse-liability",
                    "label": "Training Data Misuse Liability",
                },
                {
                    "value": "data-poisoning-adversarial-attack",
                    "label": "Data Poisoning & Adversarial Attack",
                },
                {
                    "value": "service-interruption-liability",
                    "label": "Service Interruption Liability",
                },
                {
                    "value": "bodily-injury-property-damage-autonomous-ai",
                    "label": "Bodily Injury/Property Damage (Autonomous AI)",
                },
                {
                    "value": "deepfake-synthetic-media-liability",
                    "label": "Deepfake & Synthetic Media Liability",
                },
                {"value": "civil-fines-penalties", "label": "Civil Fines & Penalties"},
            ],
            "order": 10,
            "group": "ai_coverage",
        },
    ],
    "conditional_logic": {
        "rules": [
            {
                "target_field": "incident_details",
                "action": "show",
                "conditions": [
                    {
                        "field_key": "has_prior_incidents",
                        "operator": "equals",
                        "value": True,
                    }
                ],
                "match": "all",
            },
            {
                "target_field": "wants_ai_coverage",
                "action": "show",
                "conditions": [
                    {"field_key": "uses_ai", "operator": "equals", "value": True}
                ],
                "match": "all",
            },
            {
                "target_field": "ai_coverage_options",
                "action": "show",
                "conditions": [
                    {"field_key": "uses_ai", "operator": "equals", "value": True},
                    {
                        "field_key": "wants_ai_coverage",
                        "operator": "equals",
                        "value": True,
                    },
                ],
                "match": "all",
            },
        ]
    },
    "rating_field_mappings": {
        "services_description": "services_description",
        "service_criticality": "service_criticality",
        "industry_hazards": "industry_hazards",
        "has_liability_protections": "has_liability_protections",
        "has_quality_assurance": "has_quality_assurance",
        "has_prior_incidents": "has_prior_incidents",
        "incident_details": "incident_details",
        "uses_ai": "uses_ai",
        "wants_ai_coverage": "wants_ai_coverage",
        "ai_coverage_options": "ai_coverage_options",
    },
}


# ═════════════════════════════════════════════════════════════════════
# 4. Cyber Liability
# ═════════════════════════════════════════════════════════════════════

CYBER_FORM = {
    "name": "Cyber Liability Questionnaire",
    "slug": "cyber-questionnaire",
    "version": 1,
    "description": "Dynamic questionnaire for Cyber Liability coverage rating.",
    "coverage_type": "cyber-liability",
    "is_active": True,
    "fields": [
        {
            "key": "employee_band",
            "label": "Number of employees",
            "field_type": "select",
            "required": True,
            "options": [
                {"value": "under_25", "label": "Under 25"},
                {"value": "25_50", "label": "25 - 50"},
                {"value": "50_250", "label": "50 - 250"},
                {"value": "250_500", "label": "250 - 500"},
                {"value": "500_1000", "label": "500 - 1,000"},
                {"value": "over_1000", "label": "Over 1,000"},
            ],
            "order": 1,
            "group": "company_profile",
        },
        {
            "key": "sensitive_record_count",
            "label": "How many sensitive records do you store?",
            "field_type": "select",
            "required": True,
            "help_text": "PII, PHI, payment data, etc.",
            "options": [
                {"value": "under_10k", "label": "Under 10,000"},
                {"value": "10k_100k", "label": "10,000 - 100,000"},
                {"value": "100k_1m", "label": "100,000 - 1,000,000"},
                {"value": "over_1m", "label": "Over 1,000,000"},
            ],
            "order": 2,
            "group": "company_profile",
        },
        {
            "key": "data_systems_exposure",
            "label": "Data and systems exposure",
            "field_type": "checkbox_group",
            "help_text": "Select all that apply.",
            "options": [
                {
                    "value": "stores-sensitive-data",
                    "label": "Stores sensitive customer data (PII/PHI/PCI)",
                },
                {
                    "value": "maintains-large-volume-data",
                    "label": "Maintains large volume of data records",
                },
                {
                    "value": "critical-tech-service",
                    "label": "Provides a critical technology service to clients",
                },
            ],
            "order": 3,
            "group": "company_profile",
        },
        {
            "key": "all_users_have_unique_logins",
            "label": "Do all users have unique login credentials?",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 4,
            "group": "security",
        },
        {
            "key": "security_controls",
            "label": "Which security controls are in place?",
            "field_type": "checkbox_group",
            "help_text": "Select all that apply.",
            "options": [
                {
                    "value": "mfa-required",
                    "label": "Multi-factor authentication required",
                },
                {
                    "value": "backups-incident-plan",
                    "label": "Regular backups and incident response plan",
                },
                {
                    "value": "security-training",
                    "label": "Employee security awareness training",
                },
                {
                    "value": "security-assessments",
                    "label": "Regular security assessments / pen testing",
                },
            ],
            "order": 5,
            "group": "security",
        },
        {
            "key": "security_framework_certified",
            "label": "Are you certified under a security framework (SOC 2, ISO 27001, etc.)?",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": "yes", "label": "Yes"},
                {"value": "no", "label": "No"},
                {"value": "in-progress", "label": "In Progress"},
            ],
            "order": 6,
            "group": "security",
        },
        {
            "key": "outsources_it",
            "label": "Do you outsource IT management?",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 7,
            "group": "security",
        },
        {
            "key": "requires_vendor_security",
            "label": "Do you require vendors to meet security standards?",
            "field_type": "radio",
            "options": [
                {"value": "Yes", "label": "Yes"},
                {"value": "No", "label": "No"},
                {"value": "N/A", "label": "N/A"},
            ],
            "order": 8,
            "group": "security",
        },
        {
            "key": "regulations_subject_to",
            "label": "Which regulations apply to your business?",
            "field_type": "checkbox_group",
            "options": [
                {"value": "none", "label": "None"},
                {"value": "gdpr", "label": "GDPR"},
                {"value": "ccpa-cpra", "label": "CCPA/CPRA"},
                {"value": "hipaa", "label": "HIPAA"},
                {"value": "glba", "label": "GLBA"},
            ],
            "order": 9,
            "group": "compliance",
        },
        {
            "key": "regulatory_sublimit",
            "label": "Regulatory defense sublimit (% of policy limit)",
            "field_type": "select",
            "required": True,
            "options": [
                {"value": "0", "label": "0%"},
                {"value": "5", "label": "5%"},
                {"value": "10", "label": "10%"},
                {"value": "25", "label": "25%"},
                {"value": "50", "label": "50%"},
                {"value": "100", "label": "100%"},
            ],
            "order": 10,
            "group": "compliance",
        },
        {
            "key": "wants_hipaa_penalties_coverage",
            "label": "Do you want HIPAA penalties coverage?",
            "field_type": "radio",
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 11,
            "group": "compliance",
        },
        {
            "key": "maintained_compliance",
            "label": "Are you in compliance with applicable regulations?",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 12,
            "group": "compliance",
        },
        {
            "key": "compliance_issues_description",
            "label": "Describe compliance issues",
            "field_type": "textarea",
            "placeholder": "Describe the nature of compliance gaps...",
            "order": 13,
            "group": "compliance",
            "validation": {"max_length": 2000},
        },
        {
            "key": "has_past_incidents",
            "label": "Have you experienced any cyber incidents or data breaches?",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 14,
            "group": "claims",
        },
        {
            "key": "incident_details",
            "label": "Describe past incidents",
            "field_type": "textarea",
            "placeholder": "Describe incidents, dates, records affected, and remediation...",
            "order": 15,
            "group": "claims",
            "validation": {"max_length": 3000},
        },
    ],
    "conditional_logic": {
        "rules": [
            {
                "target_field": "requires_vendor_security",
                "action": "show",
                "conditions": [
                    {"field_key": "outsources_it", "operator": "equals", "value": True}
                ],
                "match": "all",
            },
            {
                "target_field": "wants_hipaa_penalties_coverage",
                "action": "show",
                "conditions": [
                    {
                        "field_key": "regulations_subject_to",
                        "operator": "contains",
                        "value": "hipaa",
                    }
                ],
                "match": "all",
            },
            {
                "target_field": "compliance_issues_description",
                "action": "show",
                "conditions": [
                    {
                        "field_key": "maintained_compliance",
                        "operator": "equals",
                        "value": False,
                    }
                ],
                "match": "all",
            },
            {
                "target_field": "incident_details",
                "action": "show",
                "conditions": [
                    {
                        "field_key": "has_past_incidents",
                        "operator": "equals",
                        "value": True,
                    }
                ],
                "match": "all",
            },
        ]
    },
    "rating_field_mappings": {
        "employee_band": "employee_band",
        "sensitive_record_count": "sensitive_record_count",
        "data_systems_exposure": "data_systems_exposure",
        "all_users_have_unique_logins": "all_users_have_unique_logins",
        "security_controls": "security_controls",
        "security_framework_certified": "security_framework_certified",
        "outsources_it": "outsources_it",
        "requires_vendor_security": "requires_vendor_security",
        "regulations_subject_to": "regulations_subject_to",
        "regulatory_sublimit": "regulatory_sublimit",
        "wants_hipaa_penalties_coverage": "wants_hipaa_penalties_coverage",
        "maintained_compliance": "maintained_compliance",
        "has_past_incidents": "has_past_incidents",
        "incident_details": "incident_details",
    },
}


# ═════════════════════════════════════════════════════════════════════
# 5. Fiduciary Liability
# ═════════════════════════════════════════════════════════════════════

FIDUCIARY_FORM = {
    "name": "Fiduciary Liability Questionnaire",
    "slug": "fiduciary-questionnaire",
    "version": 1,
    "description": "Dynamic questionnaire for Fiduciary Liability coverage rating.",
    "coverage_type": "fiduciary-liability",
    "is_active": True,
    "fields": [
        {
            "key": "benefit_plan_types",
            "label": "What types of benefit plans do you offer?",
            "field_type": "checkbox_group",
            "required": True,
            "options": [
                {"value": "401k", "label": "401(k)"},
                {"value": "pension", "label": "Pension / Defined Benefit"},
                {"value": "health", "label": "Health Insurance"},
                {"value": "welfare", "label": "Welfare Benefits"},
                {"value": "other", "label": "Other"},
            ],
            "order": 1,
            "group": "plans",
        },
        {
            "key": "benefit_plan_other_description",
            "label": "Describe other benefit plans",
            "field_type": "textarea",
            "placeholder": "Describe the other benefit plans...",
            "order": 2,
            "group": "plans",
            "validation": {"max_length": 1000},
        },
        {
            "key": "total_plan_assets",
            "label": "Total plan assets under management",
            "field_type": "select",
            "required": True,
            "options": [
                {"value": "under_100k", "label": "Under $100,000"},
                {"value": "100k_500k", "label": "$100,000 - $500,000"},
                {"value": "500k_1m", "label": "$500,000 - $1,000,000"},
                {"value": "1m_5m", "label": "$1M - $5M"},
                {"value": "5m_25m", "label": "$5M - $25M"},
                {"value": "25m_100m", "label": "$25M - $100M"},
                {"value": "over_100m", "label": "Over $100M"},
            ],
            "order": 3,
            "group": "plans",
        },
        {
            "key": "has_defined_benefit_plan",
            "label": "Do you have a defined benefit (pension) plan?",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 4,
            "group": "plans",
        },
        {
            "key": "defined_benefit_funding_percent",
            "label": "Defined benefit plan funding percentage",
            "field_type": "percentage",
            "placeholder": "e.g. 85",
            "help_text": "What percentage of the defined benefit obligation is funded?",
            "validation": {"min": 0, "max": 200},
            "order": 5,
            "group": "plans",
            "width": "half",
        },
        {
            "key": "has_company_stock_in_plan",
            "label": "Does any plan hold company stock?",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 6,
            "group": "investments",
        },
        {
            "key": "company_stock_details",
            "label": "Company stock details",
            "field_type": "textarea",
            "placeholder": "Describe company stock holdings in plans...",
            "order": 7,
            "group": "investments",
            "validation": {"max_length": 1000},
        },
        {
            "key": "review_frequency",
            "label": "How often are plan investments reviewed?",
            "field_type": "select",
            "required": True,
            "options": [
                {"value": "annually", "label": "Annually"},
                {"value": "every-2-years", "label": "Every 2 years"},
                {"value": "every-3-years", "label": "Every 3 years"},
                {"value": "other", "label": "Other"},
            ],
            "order": 8,
            "group": "governance",
        },
        {
            "key": "has_fiduciary_committee",
            "label": "Do you have a formal fiduciary committee?",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 9,
            "group": "governance",
        },
        {
            "key": "has_fiduciary_training",
            "label": "Do fiduciaries receive regular training?",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 10,
            "group": "governance",
        },
        {
            "key": "has_written_agreements",
            "label": "Do you have written agreements with all service providers?",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 11,
            "group": "governance",
        },
        {
            "key": "has_regulatory_issues",
            "label": "Any past or pending regulatory issues?",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 12,
            "group": "claims",
        },
        {
            "key": "has_past_claims",
            "label": "Any prior fiduciary liability claims?",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 13,
            "group": "claims",
        },
        {
            "key": "past_claims_details",
            "label": "Describe past claims",
            "field_type": "textarea",
            "placeholder": "Describe claims, dates, and outcomes...",
            "order": 14,
            "group": "claims",
            "validation": {"max_length": 3000},
        },
    ],
    "conditional_logic": {
        "rules": [
            {
                "target_field": "benefit_plan_other_description",
                "action": "show",
                "conditions": [
                    {
                        "field_key": "benefit_plan_types",
                        "operator": "contains",
                        "value": "other",
                    }
                ],
                "match": "all",
            },
            {
                "target_field": "defined_benefit_funding_percent",
                "action": "show",
                "conditions": [
                    {
                        "field_key": "has_defined_benefit_plan",
                        "operator": "equals",
                        "value": True,
                    }
                ],
                "match": "all",
            },
            {
                "target_field": "company_stock_details",
                "action": "show",
                "conditions": [
                    {
                        "field_key": "has_company_stock_in_plan",
                        "operator": "equals",
                        "value": True,
                    }
                ],
                "match": "all",
            },
            {
                "target_field": "past_claims_details",
                "action": "show",
                "conditions": [
                    {
                        "field_key": "has_past_claims",
                        "operator": "equals",
                        "value": True,
                    }
                ],
                "match": "all",
            },
        ]
    },
    "rating_field_mappings": {
        "benefit_plan_types": "benefit_plan_types",
        "total_plan_assets": "total_plan_assets",
        "has_defined_benefit_plan": "has_defined_benefit_plan",
        "defined_benefit_funding_percent": "defined_benefit_funding_percent",
        "has_company_stock_in_plan": "has_company_stock_in_plan",
        "review_frequency": "review_frequency",
        "has_fiduciary_committee": "has_fiduciary_committee",
        "has_fiduciary_training": "has_fiduciary_training",
        "has_written_agreements": "has_written_agreements",
        "has_regulatory_issues": "has_regulatory_issues",
        "has_past_claims": "has_past_claims",
    },
}


# ═════════════════════════════════════════════════════════════════════
# 6. Hired & Non-Owned Auto
# ═════════════════════════════════════════════════════════════════════

HNOA_FORM = {
    "name": "Hired & Non-Owned Auto Questionnaire",
    "slug": "hnoa-questionnaire",
    "version": 1,
    "description": "Dynamic questionnaire for HNOA coverage rating.",
    "coverage_type": "hired-and-non-owned-auto",
    "is_active": True,
    "fields": [
        {
            "key": "driver_band",
            "label": "How many employees drive for business purposes?",
            "field_type": "select",
            "required": True,
            "options": [
                {"value": "0_5", "label": "0 - 5"},
                {"value": "6_10", "label": "6 - 10"},
                {"value": "11_25", "label": "11 - 25"},
                {"value": "26_50", "label": "26 - 50"},
                {"value": "51_100", "label": "51 - 100"},
                {"value": "101_250", "label": "101 - 250"},
                {"value": "251_500", "label": "251 - 500"},
                {"value": "501_1000", "label": "501 - 1,000"},
                {"value": "1001_2000", "label": "1,001 - 2,000"},
                {"value": "2001_plus", "label": "2,001+"},
            ],
            "order": 1,
            "group": "drivers",
        },
        {
            "key": "has_drivers_under_25",
            "label": "Are any drivers under age 25?",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 2,
            "group": "drivers",
        },
        {
            "key": "driving_frequency",
            "label": "How frequently do employees drive for business?",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": "rarely", "label": "Rarely (a few times per month)"},
                {"value": "occasionally", "label": "Occasionally (weekly)"},
                {"value": "regularly", "label": "Regularly (daily)"},
            ],
            "order": 3,
            "group": "usage",
        },
        {
            "key": "travel_distance",
            "label": "Typical travel distance",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": "local", "label": "Local (within metro area)"},
                {"value": "long-distance", "label": "Long-distance (interstate)"},
            ],
            "order": 4,
            "group": "usage",
        },
        {
            "key": "has_driver_safety_measures",
            "label": "Do you have a formal driver safety program?",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 5,
            "group": "safety",
        },
        {
            "key": "rents_vehicles",
            "label": "Does your company rent vehicles?",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 6,
            "group": "vehicles",
        },
        {
            "key": "rental_vehicle_details",
            "label": "Describe rental vehicle usage",
            "field_type": "textarea",
            "placeholder": "Frequency, types of vehicles, typical use...",
            "order": 7,
            "group": "vehicles",
            "validation": {"max_length": 1000},
        },
        {
            "key": "has_high_value_vehicles",
            "label": "Do you regularly rent high-value vehicles (luxury, specialty)?",
            "field_type": "radio",
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 8,
            "group": "vehicles",
        },
        {
            "key": "high_value_vehicle_details",
            "label": "Describe high-value vehicle usage",
            "field_type": "textarea",
            "placeholder": "Types of vehicles and frequency...",
            "order": 9,
            "group": "vehicles",
            "validation": {"max_length": 1000},
        },
        {
            "key": "has_past_auto_incidents",
            "label": "Any prior auto incidents or claims?",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 10,
            "group": "claims",
        },
        {
            "key": "past_auto_incident_details",
            "label": "Describe past auto incidents",
            "field_type": "textarea",
            "placeholder": "Describe incidents, dates, and outcomes...",
            "order": 11,
            "group": "claims",
            "validation": {"max_length": 2000},
        },
    ],
    "conditional_logic": {
        "rules": [
            {
                "target_field": "rental_vehicle_details",
                "action": "show",
                "conditions": [
                    {"field_key": "rents_vehicles", "operator": "equals", "value": True}
                ],
                "match": "all",
            },
            {
                "target_field": "has_high_value_vehicles",
                "action": "show",
                "conditions": [
                    {"field_key": "rents_vehicles", "operator": "equals", "value": True}
                ],
                "match": "all",
            },
            {
                "target_field": "high_value_vehicle_details",
                "action": "show",
                "conditions": [
                    {
                        "field_key": "rents_vehicles",
                        "operator": "equals",
                        "value": True,
                    },
                    {
                        "field_key": "has_high_value_vehicles",
                        "operator": "equals",
                        "value": True,
                    },
                ],
                "match": "all",
            },
            {
                "target_field": "past_auto_incident_details",
                "action": "show",
                "conditions": [
                    {
                        "field_key": "has_past_auto_incidents",
                        "operator": "equals",
                        "value": True,
                    }
                ],
                "match": "all",
            },
        ]
    },
    "rating_field_mappings": {
        "driver_band": "driver_band",
        "has_drivers_under_25": "has_drivers_under_25",
        "driving_frequency": "driving_frequency",
        "travel_distance": "travel_distance",
        "has_driver_safety_measures": "has_driver_safety_measures",
        "rents_vehicles": "rents_vehicles",
        "has_high_value_vehicles": "has_high_value_vehicles",
        "has_past_auto_incidents": "has_past_auto_incidents",
    },
}


# ═════════════════════════════════════════════════════════════════════
# 7. Media Liability
# ═════════════════════════════════════════════════════════════════════

MEDIA_FORM = {
    "name": "Media Liability Questionnaire",
    "slug": "media-questionnaire",
    "version": 1,
    "description": "Dynamic questionnaire for Media Liability coverage rating.",
    "coverage_type": "media-liability",
    "is_active": True,
    "fields": [
        {
            "key": "has_media_exposure",
            "label": "Does your business publish or distribute media content?",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 1,
            "group": "content",
        },
        {
            "key": "media_content_types",
            "label": "What types of content do you produce?",
            "field_type": "checkbox_group",
            "options": [
                {"value": "company-generated", "label": "Company-generated content"},
                {"value": "user-generated", "label": "User-generated content (UGC)"},
            ],
            "order": 2,
            "group": "content",
        },
        {
            "key": "original_content_volume",
            "label": "Volume of company-generated content (pieces per month)",
            "field_type": "select",
            "options": [
                {"value": "none", "label": "None"},
                {"value": "under_100", "label": "Under 100"},
                {"value": "100_999", "label": "100 - 999"},
                {"value": "1k_4999", "label": "1,000 - 4,999"},
                {"value": "5k_19999", "label": "5,000 - 19,999"},
                {"value": "20k_49999", "label": "20,000 - 49,999"},
                {"value": "50k_plus", "label": "50,000+"},
            ],
            "order": 3,
            "group": "content",
        },
        {
            "key": "ugc_content_volume",
            "label": "Volume of user-generated content (pieces per month)",
            "field_type": "select",
            "options": [
                {"value": "none", "label": "None"},
                {"value": "under_100", "label": "Under 100"},
                {"value": "100_999", "label": "100 - 999"},
                {"value": "1k_4999", "label": "1,000 - 4,999"},
                {"value": "5k_19999", "label": "5,000 - 19,999"},
                {"value": "20k_49999", "label": "20,000 - 49,999"},
                {"value": "50k_plus", "label": "50,000+"},
            ],
            "order": 4,
            "group": "content",
        },
        {
            "key": "has_content_moderation",
            "label": "Do you have content moderation processes?",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 5,
            "group": "controls",
        },
        {
            "key": "moderation_details",
            "label": "Describe content moderation processes",
            "field_type": "textarea",
            "placeholder": "Describe your moderation tools, team, and policies...",
            "order": 6,
            "group": "controls",
            "validation": {"max_length": 2000},
        },
        {
            "key": "has_media_controls",
            "label": "Do you have editorial controls and review processes?",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 7,
            "group": "controls",
        },
        {
            "key": "uses_third_party_content",
            "label": "Do you use licensed or third-party content?",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 8,
            "group": "licensing",
        },
        {
            "key": "has_licenses",
            "label": "Do you have proper licenses for all third-party content?",
            "field_type": "radio",
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 9,
            "group": "licensing",
        },
        {
            "key": "has_past_complaints",
            "label": "Any prior copyright, defamation, or IP complaints?",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 10,
            "group": "claims",
        },
        {
            "key": "past_complaint_details",
            "label": "Describe past complaints",
            "field_type": "textarea",
            "placeholder": "Describe complaints, dates, and outcomes...",
            "order": 11,
            "group": "claims",
            "validation": {"max_length": 3000},
        },
    ],
    "conditional_logic": {
        "rules": [
            {
                "target_field": "media_content_types",
                "action": "show",
                "conditions": [
                    {
                        "field_key": "has_media_exposure",
                        "operator": "equals",
                        "value": True,
                    }
                ],
                "match": "all",
            },
            {
                "target_field": "original_content_volume",
                "action": "show",
                "conditions": [
                    {
                        "field_key": "has_media_exposure",
                        "operator": "equals",
                        "value": True,
                    },
                    {
                        "field_key": "media_content_types",
                        "operator": "contains",
                        "value": "company-generated",
                    },
                ],
                "match": "all",
            },
            {
                "target_field": "ugc_content_volume",
                "action": "show",
                "conditions": [
                    {
                        "field_key": "has_media_exposure",
                        "operator": "equals",
                        "value": True,
                    },
                    {
                        "field_key": "media_content_types",
                        "operator": "contains",
                        "value": "user-generated",
                    },
                ],
                "match": "all",
            },
            {
                "target_field": "moderation_details",
                "action": "show",
                "conditions": [
                    {
                        "field_key": "has_content_moderation",
                        "operator": "equals",
                        "value": True,
                    }
                ],
                "match": "all",
            },
            {
                "target_field": "has_licenses",
                "action": "show",
                "conditions": [
                    {
                        "field_key": "uses_third_party_content",
                        "operator": "equals",
                        "value": True,
                    }
                ],
                "match": "all",
            },
            {
                "target_field": "past_complaint_details",
                "action": "show",
                "conditions": [
                    {
                        "field_key": "has_past_complaints",
                        "operator": "equals",
                        "value": True,
                    }
                ],
                "match": "all",
            },
        ]
    },
    "rating_field_mappings": {
        "has_media_exposure": "has_media_exposure",
        "media_content_types": "media_content_types",
        "original_content_volume": "original_content_volume",
        "ugc_content_volume": "ugc_content_volume",
        "has_content_moderation": "has_content_moderation",
        "has_media_controls": "has_media_controls",
        "uses_third_party_content": "uses_third_party_content",
        "has_licenses": "has_licenses",
        "has_past_complaints": "has_past_complaints",
    },
}


# ═════════════════════════════════════════════════════════════════════
# 8. Employment Practices Liability
# ═════════════════════════════════════════════════════════════════════

EPL_FORM = {
    "name": "Employment Practices Liability Questionnaire",
    "slug": "epl-questionnaire",
    "version": 1,
    "description": "Dynamic questionnaire for EPL coverage rating.",
    "coverage_type": "employment-practices-liability",
    "is_active": True,
    "fields": [
        {
            "key": "geographic_spread",
            "label": "US employee distribution by state",
            "field_type": "textarea",
            "required": True,
            "help_text": "Enter each state and employee count. This field is rendered as a structured input on the frontend.",
            "placeholder": 'e.g. [{"state": "CA", "employee_count": 10}, ...]',
            "order": 1,
            "group": "employees",
        },
        {
            "key": "international_spread",
            "label": "International employee distribution",
            "field_type": "textarea",
            "help_text": "Enter each country and employee count.",
            "placeholder": 'e.g. [{"country": "UK", "employee_count": 5}, ...]',
            "order": 2,
            "group": "employees",
        },
        {
            "key": "average_salary_level",
            "label": "Average employee salary level",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": "under-75k", "label": "Under $75,000"},
                {"value": "over-75k", "label": "Over $75,000"},
            ],
            "order": 3,
            "group": "employees",
        },
        {
            "key": "uses_contractors",
            "label": "Do you use independent contractors?",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 4,
            "group": "contractors",
        },
        {
            "key": "wants_contractor_epli",
            "label": "Would you like to add contractor EPLI coverage?",
            "field_type": "radio",
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 5,
            "group": "contractors",
        },
        {
            "key": "contractor_geographic_spread",
            "label": "US contractor distribution by state",
            "field_type": "textarea",
            "placeholder": 'e.g. [{"state": "NY", "employee_count": 3}, ...]',
            "order": 6,
            "group": "contractors",
        },
        {
            "key": "hr_policies",
            "label": "Which HR policies and practices do you have?",
            "field_type": "checkbox_group",
            "help_text": "Select all that apply.",
            "options": [
                {"value": "handbook", "label": "Employee Handbook"},
                {
                    "value": "training",
                    "label": "Anti-harassment/discrimination training",
                },
                {"value": "reporting", "label": "Anonymous reporting mechanism"},
                {
                    "value": "dedicated-hr",
                    "label": "Dedicated HR department or officer",
                },
            ],
            "order": 7,
            "group": "hr_practices",
        },
        {
            "key": "has_past_layoffs",
            "label": "Have you conducted layoffs in the past 24 months?",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 8,
            "group": "workforce",
        },
        {
            "key": "past_layoff_details",
            "label": "Describe past layoffs",
            "field_type": "textarea",
            "placeholder": "Number of employees, timing, and reasons...",
            "order": 9,
            "group": "workforce",
            "validation": {"max_length": 2000},
        },
        {
            "key": "has_planned_layoffs",
            "label": "Are any layoffs planned in the next 12 months?",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 10,
            "group": "workforce",
        },
        {
            "key": "planned_layoff_details",
            "label": "Describe planned layoffs",
            "field_type": "textarea",
            "placeholder": "Expected number, timing, and reasons...",
            "order": 11,
            "group": "workforce",
            "validation": {"max_length": 2000},
        },
        {
            "key": "has_hourly_employees",
            "label": "Do you have hourly (non-exempt) employees?",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 12,
            "group": "workforce",
        },
        {
            "key": "is_wage_compliant",
            "label": "Are you in compliance with all wage and hour laws?",
            "field_type": "radio",
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 13,
            "group": "workforce",
        },
        {
            "key": "has_third_party_interaction",
            "label": "Do employees regularly interact with third parties (customers, vendors)?",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 14,
            "group": "third_party",
        },
        {
            "key": "has_third_party_training",
            "label": "Do employees receive training on third-party interactions?",
            "field_type": "radio",
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 15,
            "group": "third_party",
        },
    ],
    "conditional_logic": {
        "rules": [
            {
                "target_field": "wants_contractor_epli",
                "action": "show",
                "conditions": [
                    {
                        "field_key": "uses_contractors",
                        "operator": "equals",
                        "value": True,
                    }
                ],
                "match": "all",
            },
            {
                "target_field": "contractor_geographic_spread",
                "action": "show",
                "conditions": [
                    {
                        "field_key": "uses_contractors",
                        "operator": "equals",
                        "value": True,
                    },
                    {
                        "field_key": "wants_contractor_epli",
                        "operator": "equals",
                        "value": True,
                    },
                ],
                "match": "all",
            },
            {
                "target_field": "past_layoff_details",
                "action": "show",
                "conditions": [
                    {
                        "field_key": "has_past_layoffs",
                        "operator": "equals",
                        "value": True,
                    }
                ],
                "match": "all",
            },
            {
                "target_field": "planned_layoff_details",
                "action": "show",
                "conditions": [
                    {
                        "field_key": "has_planned_layoffs",
                        "operator": "equals",
                        "value": True,
                    }
                ],
                "match": "all",
            },
            {
                "target_field": "is_wage_compliant",
                "action": "show",
                "conditions": [
                    {
                        "field_key": "has_hourly_employees",
                        "operator": "equals",
                        "value": True,
                    }
                ],
                "match": "all",
            },
            {
                "target_field": "has_third_party_training",
                "action": "show",
                "conditions": [
                    {
                        "field_key": "has_third_party_interaction",
                        "operator": "equals",
                        "value": True,
                    }
                ],
                "match": "all",
            },
        ]
    },
    "rating_field_mappings": {
        "geographic_spread": "geographic_spread",
        "international_spread": "international_spread",
        "average_salary_level": "average_salary_level",
        "uses_contractors": "uses_contractors",
        "wants_contractor_epli": "wants_contractor_epli",
        "contractor_geographic_spread": "contractor_geographic_spread",
        "hr_policies": "hr_policies",
        "has_past_layoffs": "has_past_layoffs",
        "has_planned_layoffs": "has_planned_layoffs",
        "has_hourly_employees": "has_hourly_employees",
        "is_wage_compliant": "is_wage_compliant",
        "has_third_party_interaction": "has_third_party_interaction",
        "has_third_party_training": "has_third_party_training",
    },
}


# ═════════════════════════════════════════════════════════════════════
# 9. Custom Crime (brokered coverage)
# ─────────────────────────────────────────────────────────────────────
# Version history:
#   v1 — initial questionnaire (legacy; older quotes were started on v1)
#   v2 — added required fields: ``software_fraud_detection``,
#        ``edp_authorized_documented``, ``separate_deposit_person``,
#        ``separate_withdrawal_person``. These align with the rating
#        engine's CrimeQuestionnaire (api/rating/questionnaires/crime.py)
#        and MUST be present on every submission, even if the quote was
#        started on v1.
# ═════════════════════════════════════════════════════════════════════

CRIME_FORM = {
    "name": "Crime Coverage Questionnaire",
    "slug": "crime-questionnaire",
    "version": 2,
    "description": "Dynamic questionnaire for Crime coverage rating.",
    "coverage_type": "custom-crime",
    "is_active": True,
    "fields": [
        {
            "key": "hiring_process_checks",
            "label": "Which background checks does your hiring process include?",
            "field_type": "checkbox_group",
            "required": True,
            "options": [
                {
                    "value": "prior-employment-verification",
                    "label": "Prior Employment Verification",
                },
                {"value": "drug-testing", "label": "Drug Testing"},
                {"value": "education-verification", "label": "Education Verification"},
                {"value": "credit-history", "label": "Credit History"},
                {"value": "criminal-history", "label": "Criminal History"},
                {"value": "none", "label": "None"},
            ],
            "order": 1,
            "group": "hiring",
        },
        {
            "key": "segregation_cash_receipts",
            "label": "Is there segregation of duties for cash receipts?",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": "yes", "label": "Yes"},
                {"value": "no", "label": "No"},
                {"value": "not-applicable", "label": "Not Applicable"},
            ],
            "order": 2,
            "group": "internal_controls",
        },
        {
            "key": "authority_separated",
            "label": "Is signing authority separated from bookkeeping authority?",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 3,
            "group": "internal_controls",
        },
        {
            "key": "segregation_areas",
            "label": "Which additional segregation-of-duties areas apply?",
            "field_type": "checkbox_group",
            "required": True,
            "options": [
                {"value": "blank-checks-oversight", "label": "Blank checks oversight"},
                {
                    "value": "purchase-order-approval",
                    "label": "Purchase order approval",
                },
                {"value": "vendor-approval", "label": "Vendor approval"},
                {"value": "none", "label": "None"},
            ],
            "order": 4,
            "group": "internal_controls",
        },
        {
            "key": "segregation_inventory_management",
            "label": "Is there segregation of duties for inventory management?",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": "yes", "label": "Yes"},
                {"value": "no", "label": "No"},
                {"value": "not-applicable", "label": "Not Applicable"},
            ],
            "order": 5,
            "group": "internal_controls",
        },
        # ── New required fields introduced in v2 ──────────────────────
        # These are the drift fields: older quotes created on v1 will
        # NOT have them populated, so the backend must re-validate
        # against the latest version at submit time.
        {
            "key": "software_fraud_detection",
            "label": "Do you use software-based fraud detection?",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 6,
            "group": "controls",
        },
        {
            "key": "edp_authorized_documented",
            "label": "Are EDP access rights authorized and documented?",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 7,
            "group": "controls",
        },
        {
            "key": "separate_deposit_person",
            "label": "Is the person making deposits different from the one recording them?",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 8,
            "group": "controls",
        },
        {
            "key": "separate_withdrawal_person",
            "label": "Is the person authorizing withdrawals different from the one recording them?",
            "field_type": "radio",
            "required": True,
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
            ],
            "order": 9,
            "group": "controls",
        },
    ],
    "conditional_logic": {"rules": []},
    "rating_field_mappings": {
        "hiring_process_checks": "hiring_process_checks",
        "segregation_cash_receipts": "segregation_cash_receipts",
        "authority_separated": "authority_separated",
        "segregation_areas": "segregation_areas",
        "segregation_inventory_management": "segregation_inventory_management",
        "software_fraud_detection": "software_fraud_detection",
        "edp_authorized_documented": "edp_authorized_documented",
        "separate_deposit_person": "separate_deposit_person",
        "separate_withdrawal_person": "separate_withdrawal_person",
    },
}


# ═════════════════════════════════════════════════════════════════════
# All forms registry
# ═════════════════════════════════════════════════════════════════════

ALL_FORMS = [
    CGL_FORM,
    DO_FORM,
    TECH_EO_FORM,
    CYBER_FORM,
    FIDUCIARY_FORM,
    HNOA_FORM,
    MEDIA_FORM,
    EPL_FORM,
    CRIME_FORM,
]
