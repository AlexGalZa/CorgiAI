-- AIB Database Schema

-- Sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status VARCHAR(20) DEFAULT 'active',  -- active, completed, abandoned
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);

-- Messages table (full transcript)
CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    role VARCHAR(10) NOT NULL,  -- 'user' or 'assistant'
    content TEXT NOT NULL,
    attachments JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Extracted intake data (the broker packet)
CREATE TABLE IF NOT EXISTS intakes (
    id SERIAL PRIMARY KEY,
    session_id UUID UNIQUE REFERENCES sessions(id) ON DELETE CASCADE,
    company_name VARCHAR(255),
    dba VARCHAR(255),
    address TEXT,
    fein VARCHAR(20),
    business_description TEXT,
    annual_revenue VARCHAR(100),
    employees_total VARCHAR(50),
    employees_ft_pt VARCHAR(100),
    annual_payroll VARCHAR(100),
    policy_type VARCHAR(100),
    total_limit_requested VARCHAR(100),
    existing_policies TEXT,
    financials_available VARCHAR(100),
    records_count VARCHAR(100),
    cyber_incidents TEXT,
    shareholders_5pct TEXT,
    fye_financials VARCHAR(100),
    last_12mo_revenue VARCHAR(100),
    epl_international_entities TEXT,
    epl_claims TEXT,
    erisa_plan_assets VARCHAR(100),
    media_content_type TEXT,
    contract_required BOOLEAN DEFAULT FALSE,
    contract_provided BOOLEAN DEFAULT FALSE,
    uploaded_documents JSONB DEFAULT '[]',
    client_questions_flagged JSONB DEFAULT '[]',
    additional_notes TEXT,
    raw_extraction JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_intakes_session ON intakes(session_id);

-- Additive migrations (safe to re-run)
ALTER TABLE intakes ADD COLUMN IF NOT EXISTS years_in_business VARCHAR(50);
ALTER TABLE intakes ADD COLUMN IF NOT EXISTS prior_carrier VARCHAR(255);
ALTER TABLE intakes ADD COLUMN IF NOT EXISTS retroactive_date VARCHAR(50);
ALTER TABLE intakes ADD COLUMN IF NOT EXISTS desired_effective_date VARCHAR(50);
ALTER TABLE intakes ADD COLUMN IF NOT EXISTS claims_history TEXT;
ALTER TABLE intakes ADD COLUMN IF NOT EXISTS cyber_mfa BOOLEAN;
ALTER TABLE intakes ADD COLUMN IF NOT EXISTS cyber_backups BOOLEAN;
ALTER TABLE intakes ADD COLUMN IF NOT EXISTS cyber_endpoint_security BOOLEAN;
