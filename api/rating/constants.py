DO_INDUSTRY_GROUPS = ["group1", "group2", "group3", "group4", "group5", "group6"]

TECH_EO_HAZARD_CLASSES = [
    "nonprofit-commerce",
    "dev-tools",
    "ecommerce-enablement",
    "b2c-apps",
    "b2b-saas",
    "marketplace",
    "adtech-martech",
    "data-analytics",
    "it-services",
    "iot-hardware",
    "ai-ml",
    "healthtech",
    "ai-regulated",
    "fintech-consumer",
    "fintech-lending",
    "fintech-infrastructure",
    "crypto-web3",
]

EPL_INDUSTRY_GROUPS = [
    "developer-tools",
    "b2b-saas",
    "semiconductors",
    "edtech",
    "consulting",
    "it-services",
    "adtech-martech",
    "hardware-iot",
    "cleantech",
    "ai-ml",
    "healthtech",
    "ecommerce",
    "fintech",
    "crypto-web3",
    "gaming",
    "social-ugc",
    "marketplace",
    "eor",
    "other",
]

CGL_HAZARD_LEVELS = ["low-hazard", "moderate-hazard", "elevated-hazard", "high-hazard"]

DO_INDUSTRY_PROMPT = """You are an insurance underwriting assistant that classifies businesses into industry risk groups for Directors & Officers (D&O) liability insurance.

Industry groups represent risk levels from lowest (group1) to highest (group6):
- group1 (0.75x): Very low risk - Traditional, stable industries (e.g., established manufacturing, utilities, agriculture)
- group2 (1.00x): Low risk - Standard business services (e.g., professional services, retail, wholesale)
- group3 (1.25x): Moderate risk - Growth industries (e.g., technology services, media, telecom)
- group4 (1.50x): Elevated risk - High-growth tech (e.g., SaaS, fintech, e-commerce platforms)
- group5 (1.75x): High risk - Emerging/volatile sectors (e.g., crypto, AI startups, biotech)
- group6 (2.00x): Very high risk - Highly speculative ventures (e.g., unproven business models, regulated industries with compliance risks)

Consider factors like: regulatory exposure, litigation history in the sector, financial volatility, governance complexity, and stakeholder risks."""

TECH_EO_HAZARD_PROMPT = """You are an insurance underwriting assistant that classifies technology companies into hazard classes for Technology Errors & Omissions (Tech E&O) insurance.

Hazard classes represent risk levels with corresponding factors:
- nonprofit-commerce (0.70x): Non-profit tech, charitable platforms
- dev-tools (0.90x): Developer tools, IDEs, code infrastructure
- ecommerce-enablement (0.95x): Shopify-like platforms, payment processing tools
- b2c-apps (1.00x): Consumer mobile apps, lifestyle apps
- b2b-saas (1.10x): Business software, productivity tools, CRM
- marketplace (1.20x): Two-sided marketplaces, gig economy platforms
- adtech-martech (1.20x): Advertising tech, marketing automation
- data-analytics (1.25x): Data processing, business intelligence
- it-services (1.25x): Managed services, consulting, implementation
- iot-hardware (1.30x): Connected devices, smart hardware
- ai-ml (1.30x): AI/ML products (non-regulated)
- healthtech (1.35x): Healthcare tech, patient data, medical software
- ai-regulated (1.40x): AI in regulated industries (healthcare, finance)
- fintech-consumer (1.45x): Consumer financial apps, budgeting, payments
- fintech-lending (1.50x): Lending platforms, credit decisioning
- fintech-infrastructure (1.55x): Banking infrastructure, core banking
- crypto-web3 (1.70x): Cryptocurrency, blockchain, DeFi, NFTs

Consider: data sensitivity, regulatory requirements, potential for financial loss, system criticality."""

EPL_INDUSTRY_PROMPT = """You are an insurance underwriting assistant that classifies businesses into industry groups for Employment Practices Liability (EPL) insurance.

Industry groups represent employment risk levels with corresponding factors:
- developer-tools (0.95x): Low turnover, skilled workforce
- b2b-saas (1.10x): Standard tech company risks
- semiconductors (1.15x): Technical workforce, specialized skills
- edtech (1.20x): Education technology
- consulting (1.20x): Professional services, client-facing
- it-services (1.25x): Services-based, contractor mix
- adtech-martech (1.25x): Marketing tech, sales-heavy culture
- hardware-iot (1.25x): Manufacturing elements, diverse workforce
- cleantech (1.30x): Growth sector, scaling challenges
- ai-ml (1.35x): Competitive hiring, retention challenges
- healthtech (1.35x): Regulatory workforce requirements
- ecommerce (1.40x): High volume hiring, hourly workers
- fintech (1.40x): Regulatory scrutiny, compliance culture
- crypto-web3 (1.45x): Volatile industry, startup culture
- gaming (1.50x): Crunch culture, burnout risks
- social-ugc (1.55x): Content moderation stress, trust & safety
- marketplace (1.65x): Gig economy classification risks, contractor disputes
- eor (2.75x): Employer of Record - HIGHEST RISK. Companies that serve as the legal employer for client workforces globally. Extreme exposure due to employment liability across multiple jurisdictions, worker classification risks, international labor law compliance, and direct employment relationship with potentially thousands of workers they do not directly manage.

IMPORTANT: If a company describes itself as an "Employer of Record", "EOR", "Global Employment", "International PEO", or provides services where they become the legal employer for other companies' workers, classify as "eor".

Consider: workforce composition, turnover rates, contractor usage, regulatory requirements, culture risks."""

CGL_EXPOSURES_PROMPT = """You are an insurance underwriting assistant that reviews additional liability exposures for Commercial General Liability (CGL) insurance.

Your task is to assess whether the described exposures warrant upgrading the hazard classification:
- low-hazard: Office-only operations, minimal public interaction
- moderate-hazard: Standard business operations, some public interaction
- elevated-hazard: Physical operations, equipment use, moderate public exposure
- high-hazard: Construction, manufacturing, hazardous materials, significant injury risk

Exposures that may warrant upgrade:
- Physical activities with injury risk (events, sports, fitness)
- Food/beverage service
- Childcare or vulnerable population interaction
- Transportation or delivery services
- Use of heavy equipment or machinery
- Work at heights or confined spaces
- Hazardous materials handling
- Large public gatherings

Be conservative - only recommend upgrade if exposures meaningfully increase third-party bodily injury or property damage risk."""

CGL_PRODUCTS_OPERATIONS_PROMPT = """You are an insurance underwriting assistant that assesses risk for Products & Completed Operations coverage in Commercial General Liability (CGL) insurance.

Your task is to analyze the described products or completed operations and assign a risk multiplier between 1.1 and 1.5.

Risk factors to consider:
- Type of product/work: Physical products vs services, complexity
- Installation complexity: Simple delivery vs complex installation
- Customer interaction: Whether work involves customer property or end users
- Potential for bodily injury: Risk of product defects or workmanship issues causing harm
- Property damage potential: Risk of damage to customer property
- Duration of exposure: How long the product/work could cause issues after completion

Multiplier guidance:
- 1.1x: Low risk - Simple products, no installation, minimal customer interaction (e.g., software with physical packaging, office supplies)
- 1.2x: Low-moderate risk - Basic products or simple installations (e.g., furniture assembly, basic equipment setup)
- 1.3x: Moderate risk - Products with customer interaction or moderate installation (e.g., appliance installation, custom equipment, hardware deployment)
- 1.4x: Elevated risk - Complex installations or products with significant use (e.g., HVAC work, electrical equipment, construction build-outs)
- 1.5x: High risk - Critical systems, structural work, or high-consequence products (e.g., structural modifications, medical devices, safety equipment)

Analyze the description carefully and provide a multiplier that reflects the risk exposure."""

MONTHLY_BILLING_MULTIPLIER = 1 / 0.9

STATE_TAX_RATES = {
    "AK": 1.027,
    "AL": 1.036,
    "AR": 1.04,
    "AZ": 1.017,
    "CA": 1.0235,
    "CO": 1.02,
    "CT": 1.04,
    "DC": 1.017,
    "DE": 1.02,
    "FL": 1.0494,
    "GA": 1.04,
    "IA": 1.0095,
    "ID": 1.015,
    "IL": 1.005,
    "IN": 1.013,
    "KS": 1.03,
    "KY": 1.038,
    "MA": 1.0228,
    "MD": 1.02,
    "ME": 1.02,
    "MI": 1.025,
    "MN": 1.02,
    "MO": 1.02,
    "MS": 1.03,
    "MT": 1.0275,
    "NC": 1.0185,
    "ND": 1.0175,
    "NE": 1.01,
    "NH": 1.0125,
    "NJ": 1.05,
    "NM": 1.03003,
    "NV": 1.02,
    "NY": 1.02,
    "OH": 1.05,
    "OK": 1.0225,
    "PA": 1.02,
    "RI": 1.02,
    "SC": 1.0125,
    "SD": 1.025,
    "TN": 1.025,
    "TX": 1.016,
    "UT": 1.0225,
    "VA": 1.0225,
    "VT": 1.02,
    "WA": 1.02,
    "WI": 1.03,
    "WV": 1.0455,
    "WY": 1.0075,
}


STRIPE_PROCESSING_FEE_MULTIPLIER = 1.029

# ── Surplus Lines Tax Rates (non-admitted policies) ───────────────────────────
# These are the surplus lines tax rates charged by each state on non-admitted
# premium. Distinct from the admitted state tax rates above.
# Sources: NAPSLO/WSIA state filings guide, updated 2025.
# Format: decimal (e.g. 0.03 = 3%)
SURPLUS_LINES_TAX_RATES = {
    "AL": 0.06,  # 6%
    "AK": 0.03,  # 3%
    "AZ": 0.03,  # 3%
    "AR": 0.04,  # 4%
    "CA": 0.03,  # 3%
    "CO": 0.03,  # 3%
    "CT": 0.04,  # 4%
    "DC": 0.02,  # 2%
    "DE": 0.03,  # 3%
    "FL": 0.05,  # 5%
    "GA": 0.04,  # 4%
    "GU": 0.05,  # 5%
    "HI": 0.047,  # 4.7%
    "ID": 0.0150,  # 1.5%
    "IL": 0.035,  # 3.5%
    "IN": 0.025,  # 2.5%
    "IA": 0.06,  # 6%
    "KS": 0.06,  # 6%
    "KY": 0.03,  # 3%
    "LA": 0.05,  # 5%
    "ME": 0.03,  # 3%
    "MD": 0.03,  # 3%
    "MA": 0.04,  # 4%
    "MI": 0.02,  # 2%
    "MN": 0.03,  # 3%
    "MS": 0.04,  # 4%
    "MO": 0.05,  # 5%
    "MT": 0.0275,  # 2.75%
    "NE": 0.03,  # 3%
    "NV": 0.03,  # 3%
    "NH": 0.03,  # 3%
    "NJ": 0.03,  # 3%
    "NM": 0.03,  # 3%
    "NY": 0.038,  # 3.8%
    "NC": 0.05,  # 5%
    "ND": 0.02,  # 2%
    "OH": 0.05,  # 5%
    "OK": 0.025,  # 2.5%
    "OR": 0.03,  # 3%
    "PA": 0.03,  # 3%
    "PR": 0.05,  # 5%
    "RI": 0.04,  # 4%
    "SC": 0.06,  # 6%
    "SD": 0.025,  # 2.5%
    "TN": 0.05,  # 5%
    "TX": 0.0485,  # 4.85%
    "UT": 0.0421,  # 4.21% (includes stamping fee)
    "VT": 0.03,  # 3%
    "VA": 0.025,  # 2.5%
    "VI": 0.05,  # 5%
    "WA": 0.02,  # 2%
    "WV": 0.04,  # 4%
    "WI": 0.03,  # 3%
    "WY": 0.02,  # 2%
}

# Surplus lines filing deadlines by state (calendar days after binding)
SURPLUS_LINES_FILING_DEADLINES = {
    "default": 30,
    "CA": 30,
    "FL": 30,
    "TX": 60,
    "NY": 30,
    "IL": 30,
    "PA": 45,
    "OH": 30,
    "NJ": 30,
    "GA": 30,
    "NC": 30,
    "MI": 30,
    "VA": 30,
    "WA": 30,
    "AZ": 20,
    "CO": 45,
    "MN": 30,
    "MO": 15,
    "WI": 30,
    "CT": 30,
    "MD": 30,
    "OR": 30,
    "IN": 30,
    "MA": 30,
    "TN": 30,
    "SC": 45,
}

# Stamping offices by state (for filing routing)
SURPLUS_LINES_STAMPING_OFFICES = {
    "CA": "Surplus Line Association of California (SLA)",
    "FL": "Florida Surplus Lines Service Office (FSLSO)",
    "TX": "Texas Surplus Lines Stamping Office (TSLSO)",
    "IL": "Illinois Surplus Line Association",
    "NY": "New York Excess Lines Association (NYELA)",
    "GA": "Georgia Excess Lines Association (GELA)",
}
