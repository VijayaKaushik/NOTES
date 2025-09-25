-- ================================================================
-- EQUITY MANAGEMENT SYSTEM - DATABASE SCHEMA WITH BUSINESS CONTEXT
-- ================================================================

-- BUSINESS RULE: All inter-schema joins use hub_key fields (UUID surrogate keys)
-- PERFORMANCE: Hub keys are clustered indexes for optimal join performance

-- ================================================================
-- CLIENTS SCHEMA: Company Master Data
-- ================================================================

CREATE TABLE clients.client_latest (
    client_hub_key UUID PRIMARY KEY,
    client_name VARCHAR(255) NOT NULL,
    fiscal_year_end DATE NOT NULL, -- BUSINESS RULE: Drives Q1-Q4 date calculations
    incorporation_country VARCHAR(3), -- ISO country code
    stock_exchange VARCHAR(10), -- NYSE, NASDAQ, LSE, etc.
    ticker_symbol VARCHAR(10),
    
    -- AUDIT FIELDS
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    
    -- BUSINESS RULE: Fiscal year end determines quarterly reporting periods
    -- EXAMPLE DATA: 'Acme Corp', fiscal_year_end='2024-12-31' (calendar year)
    --               'TechStart Inc', fiscal_year_end='2024-03-31' (March fiscal year)
    
    INDEX idx_client_name (client_name),
    INDEX idx_fiscal_year_end (fiscal_year_end),
    INDEX idx_active_clients (is_active, client_name)
);

-- ================================================================
-- PLANS SCHEMA: Equity Compensation Plans
-- ================================================================

CREATE TABLE plans.plans (
    plan_id UUID PRIMARY KEY,
    client_hub_key UUID NOT NULL, -- RELATIONSHIP: One Client → Many Plans
    plan_name VARCHAR(255) NOT NULL,
    plan_type VARCHAR(50) NOT NULL, -- ENUM: 'ESOP', 'RSU', 'Performance', 'Director'
    
    -- BUSINESS RULES
    total_shares_authorized BIGINT, -- Max shares available under this plan
    shares_outstanding BIGINT DEFAULT 0, -- Currently granted shares
    plan_start_date DATE NOT NULL,
    plan_end_date DATE, -- NULL = ongoing plan
    
    -- ELIGIBILITY RULES (stored as JSON for flexibility)
    eligibility_criteria JSON, -- {"employee_types": ["officer", "executive"], "min_tenure_months": 12}
    
    -- AUDIT FIELDS
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    
    -- FOREIGN KEY RELATIONSHIPS
    FOREIGN KEY (client_hub_key) REFERENCES clients.client_latest(client_hub_key),
    
    -- BUSINESS RULE: Cannot grant more shares than authorized
    CONSTRAINT chk_shares_outstanding CHECK (shares_outstanding <= total_shares_authorized),
    
    -- EXAMPLE DATA: 
    -- plan_name='2024 Employee Stock Option Plan', plan_type='ESOP'
    -- plan_name='Executive RSU Program', plan_type='RSU'
    -- eligibility_criteria='{"employee_types": ["officer", "executive"], "departments": ["engineering", "sales"]}'
    
    INDEX idx_client_plans (client_hub_key, is_active),
    INDEX idx_plan_type (plan_type),
    INDEX idx_plan_dates (plan_start_date, plan_end_date)
);

CREATE TABLE plans.securities (
    security_id UUID PRIMARY KEY,
    plan_id UUID NOT NULL, -- RELATIONSHIP: One Plan → Many Securities
    security_type VARCHAR(50) NOT NULL, -- ENUM: 'ISO', 'NQSO', 'RSU', 'RSA', 'Common Stock'
    security_name VARCHAR(255) NOT NULL,
    
    -- OPTION-SPECIFIC FIELDS
    exercise_price DECIMAL(10,2), -- NULL for RSUs/RSAs
    exercise_period_years INTEGER DEFAULT 10, -- Standard 10-year option term
    
    -- BUSINESS RULES
    is_qualified_iso BOOLEAN DEFAULT false, -- Tax qualification for ISOs
    early_exercise_allowed BOOLEAN DEFAULT false,
    
    -- AUDIT FIELDS
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    
    FOREIGN KEY (plan_id) REFERENCES plans.plans(plan_id),
    
    -- BUSINESS RULE: ISOs have special tax treatment and exercise price rules
    -- EXAMPLE DATA:
    -- security_type='ISO', security_name='Incentive Stock Options', exercise_price=1.00
    -- security_type='RSU', security_name='Restricted Stock Units', exercise_price=NULL
    
    INDEX idx_plan_securities (plan_id, is_active),
    INDEX idx_security_type (security_type)
);

-- ================================================================
-- PARTICIPANTS SCHEMA: Employee Information
-- ================================================================

CREATE TABLE participants.participant_detail (
    participant_hub_key UUID PRIMARY KEY,
    participant_name VARCHAR(255) NOT NULL,
    employee_id VARCHAR(50) UNIQUE, -- Company's internal employee ID
    
    -- EMPLOYMENT STATUS - CRITICAL FOR BUSINESS RULES
    employee_type VARCHAR(50) NOT NULL, -- ENUM: 'officer', 'executive', 'director', 'employee', 'consultant'
    status VARCHAR(20) NOT NULL DEFAULT 'active', -- ENUM: 'active', 'terminated', 'leave'
    hire_date DATE NOT NULL,
    termination_date DATE, -- NULL for active employees
    
    -- BUSINESS RULE: Officers = ('officer', 'executive', 'director', 'ceo', 'cfo', 'cto')
    -- BUSINESS RULE: Active = status='active' AND (termination_date IS NULL OR termination_date > CURRENT_DATE)
    
    -- PERSONAL INFO
    email VARCHAR(255) UNIQUE,
    tax_id VARCHAR(20), -- SSN/TIN (encrypted)
    
    -- AUDIT FIELDS
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- EXAMPLE DATA:
    -- employee_type='officer', status='active', hire_date='2020-01-15', termination_date=NULL
    -- employee_type='employee', status='terminated', termination_date='2024-06-30'
    
    INDEX idx_employee_type (employee_type),
    INDEX idx_employment_status (status, termination_date),
    INDEX idx_hire_date (hire_date),
    UNIQUE INDEX idx_employee_id (employee_id)
);

CREATE TABLE participants.participant_legal_detail (
    legal_detail_id UUID PRIMARY KEY,
    participant_hub_key UUID NOT NULL, -- RELATIONSHIP: One Participant → One Legal Record
    
    -- COMPLIANCE & REGULATORY INFO
    is_section16_officer BOOLEAN DEFAULT false, -- SEC Section 16 officer status
    ownership_percentage DECIMAL(5,2) DEFAULT 0, -- Percentage ownership (for 10% rule)
    
    -- 10b5-1 TRADING PLANS
    trading_plan_type VARCHAR(50), -- '10b5-1', 'other', NULL
    trading_plan_start_date DATE,
    trading_plan_end_date DATE,
    
    -- BLACKOUT PERIODS
    blackout_start_date DATE,
    blackout_end_date DATE,
    blackout_reason VARCHAR(255), -- 'earnings', 'material_event', 'acquisition', etc.
    
    -- INSIDER TRADING TRACKING
    last_material_info_date DATE, -- When they last had material non-public info
    
    -- AUDIT FIELDS
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (participant_hub_key) REFERENCES participants.participant_detail(participant_hub_key),
    
    -- BUSINESS RULES:
    -- Section 16 Officers = employee_type IN ('ceo', 'cfo', 'director') OR ownership_percentage >= 10
    -- 10b5-1 Eligible = Section 16 officer AND no material info in last 6 months
    -- In Blackout = CURRENT_DATE BETWEEN blackout_start_date AND blackout_end_date
    
    -- EXAMPLE DATA:
    -- is_section16_officer=true, trading_plan_type='10b5-1', ownership_percentage=12.50
    -- blackout_start_date='2024-10-15', blackout_end_date='2024-11-05', blackout_reason='earnings'
    
    INDEX idx_section16_officers (is_section16_officer),
    INDEX idx_trading_plans (trading_plan_type, trading_plan_start_date),
    INDEX idx_blackout_periods (blackout_start_date, blackout_end_date),
    INDEX idx_ownership (ownership_percentage)
);

CREATE TABLE participants.participant_address (
    address_id UUID PRIMARY KEY,
    participant_hub_key UUID NOT NULL, -- RELATIONSHIP: One Participant → Many Addresses (home, work, etc.)
    address_type VARCHAR(20) DEFAULT 'primary', -- 'primary', 'work', 'mailing'
    
    -- ADDRESS COMPONENTS
    country_code VARCHAR(3) NOT NULL, -- ISO 3-letter country code
    region_code VARCHAR(10), -- State/Province/Region
    city VARCHAR(100),
    
    -- TAX JURISDICTION (critical for tax calculations)
    tax_jurisdiction VARCHAR(50), -- 'US-CA', 'US-NY', 'UK', 'CA-ON', etc.
    
    -- AUDIT FIELDS
    effective_date DATE DEFAULT CURRENT_DATE,
    end_date DATE, -- NULL = current address
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (participant_hub_key) REFERENCES participants.participant_detail(participant_hub_key),
    
    -- BUSINESS RULES:
    -- Tax Withholding by Region: US=37%, UK=45%, CA=33%, Other=25%
    -- Geographic Entity Mapping: 'US' matches ['US', 'USA', 'United States', 'U.S.']
    
    -- EXAMPLE DATA:
    -- country_code='USA', region_code='CA', tax_jurisdiction='US-CA'
    -- country_code='GBR', region_code='ENG', tax_jurisdiction='UK'
    
    INDEX idx_participant_address (participant_hub_key, effective_date),
    INDEX idx_country_region (country_code, region_code),
    INDEX idx_tax_jurisdiction (tax_jurisdiction)
);

-- ================================================================
-- GRANTS SCHEMA: Equity Awards
-- ================================================================

CREATE TABLE grants.grant_latest (
    grant_id UUID PRIMARY KEY,
    plan_id UUID NOT NULL, -- RELATIONSHIP: One Plan → Many Grants
    participant_hub_key UUID NOT NULL, -- RELATIONSHIP: One Participant → Many Grants
    security_id UUID NOT NULL, -- RELATIONSHIP: One Security → Many Grants
    
    -- GRANT DETAILS
    grant_date DATE NOT NULL,
    grant_amount BIGINT NOT NULL, -- Number of shares/units granted
    exercise_price DECIMAL(10,2), -- Strike price (for options)
    
    -- VESTING RULES
    vesting_type VARCHAR(50) DEFAULT 'time_based', -- 'time_based', 'performance', 'milestone'
    cliff_months INTEGER DEFAULT 12, -- Standard 1-year cliff
    vesting_period_months INTEGER DEFAULT 48, -- Standard 4-year vest
    
    -- PERFORMANCE CRITERIA (for performance grants)
    performance_criteria JSON, -- {"type": "revenue", "target": 100000000, "threshold": 80000000}
    performance_start_date DATE,
    performance_end_date DATE,
    
    -- ACCELERATION TRIGGERS
    acceleration_trigger VARCHAR(50), -- 'ipo', 'acquisition', 'termination_without_cause', 'death_disability'
    
    -- STATUS TRACKING
    grant_status VARCHAR(20) DEFAULT 'active', -- 'active', 'forfeited', 'expired', 'exercised'
    forfeiture_date DATE,
    expiration_date DATE, -- grant_date + exercise_period_years
    
    -- AUDIT FIELDS
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- FOREIGN KEY RELATIONSHIPS  
    FOREIGN KEY (plan_id) REFERENCES plans.plans(plan_id),
    FOREIGN KEY (participant_hub_key) REFERENCES participants.participant_detail(participant_hub_key),
    FOREIGN KEY (security_id) REFERENCES plans.securities(security_id),
    
    -- BUSINESS RULES:
    -- Cliff = No vesting until cliff_months after grant_date
    -- Standard Vesting = 25% after 1 year cliff, then monthly for remaining 3 years  
    -- Exercise Window = grant_date to grant_date + 10 years (for options)
    -- Forfeiture = If participant terminated before cliff or performance not met
    
    -- EXAMPLE DATA:
    -- grant_date='2024-01-01', grant_amount=4000, cliff_months=12, vesting_period_months=48
    -- vesting_type='performance', performance_criteria='{"metric": "revenue", "target": 50000000}'
    
    INDEX idx_participant_grants (participant_hub_key, grant_status),
    INDEX idx_plan_grants (plan_id, grant_date),
    INDEX idx_grant_dates (grant_date, expiration_date),
    INDEX idx_vesting_type (vesting_type),
    INDEX idx_performance_periods (performance_start_date, performance_end_date)
);

CREATE TABLE grants.tranches (
    tranche_id UUID PRIMARY KEY,
    grant_id UUID NOT NULL, -- RELATIONSHIP: One Grant → Many Tranches  
    tranche_number INTEGER NOT NULL, -- Sequence: 1, 2, 3, 4 (for 4-year vest)
    
    -- TRANCHE DETAILS
    tranche_shares BIGINT NOT NULL, -- Number of shares in this tranche (usually grant_amount / 4)
    tranche_percentage DECIMAL(5,2) NOT NULL, -- Usually 25.00 for equal tranches
    
    -- VESTING SCHEDULE
    cliff_date DATE, -- When this tranche can start vesting (grant_date + cliff_months)
    vesting_start_date DATE NOT NULL, -- When vesting begins for this tranche
    vesting_frequency VARCHAR(20) DEFAULT 'monthly', -- 'monthly', 'quarterly', 'annual'
    
    -- PERFORMANCE (for performance-based tranches)
    performance_achieved BOOLEAN, -- NULL = TBD, true/false = determined
    performance_measurement_date DATE,
    
    -- STATUS
    tranche_status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'vesting', 'vested', 'forfeited'
    
    -- AUDIT FIELDS
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (grant_id) REFERENCES grants.grant_latest(grant_id),
    
    -- BUSINESS RULES:
    -- Standard 4-Year Vest = 4 tranches of 25% each, starting after 1-year cliff
    -- Tranche 1: 25% vests monthly from month 13-24
    -- Tranche 2: 25% vests monthly from month 25-36  
    -- Tranche 3: 25% vests monthly from month 37-48
    -- Tranche 4: 25% vests monthly from month 49-60
    
    -- EXAMPLE DATA:
    -- grant_id='abc123', tranche_number=1, tranche_percentage=25.00, cliff_date='2025-01-01'
    -- grant_id='abc123', tranche_number=2, tranche_percentage=25.00, vesting_start_date='2026-01-01'
    
    INDEX idx_grant_tranches (grant_id, tranche_number),
    INDEX idx_vesting_dates (vesting_start_date, cliff_date),
    INDEX idx_tranche_status (tranche_status),
    UNIQUE INDEX idx_grant_tranche_number (grant_id, tranche_number)
);

-- ================================================================
-- VESTING_SCHEDULES SCHEMA: Detailed Vesting Timeline
-- ================================================================

CREATE TABLE vesting_schedules.vesting_schedules (
    schedule_id UUID PRIMARY KEY,
    tranche_id UUID NOT NULL, -- RELATIONSHIP: One Tranche → Many Vesting Events
    
    -- VESTING EVENT DETAILS
    vesting_date DATE NOT NULL, -- Specific date when shares vest
    vested_shares BIGINT NOT NULL, -- Number of shares vesting on this date
    vested_percentage DECIMAL(8,4) NOT NULL, -- Percentage of total grant (e.g., 2.0833 for monthly)
    cumulative_vested_shares BIGINT NOT NULL, -- Running total of vested shares
    
    -- VESTING TYPE
    vesting_event_type VARCHAR(50) DEFAULT 'scheduled', -- 'scheduled', 'accelerated', 'forfeited'
    acceleration_reason VARCHAR(100), -- 'ipo', 'acquisition', 'termination_without_cause', etc.
    
    -- BUSINESS CALCULATIONS (computed fields for performance)
    is_vested BOOLEAN GENERATED ALWAYS AS (vesting_date <= CURRENT_DATE) STORED,
    days_to_vesting INTEGER GENERATED ALWAYS AS (vesting_date - CURRENT_DATE) STORED,
    
    -- EXERCISE TRACKING (for options)
    is_exercised BOOLEAN DEFAULT false,
    exercise_date DATE,
    exercise_price_per_share DECIMAL(10,2), -- Price paid on exercise
    
    -- AUDIT FIELDS
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (tranche_id) REFERENCES grants.tranches(tranche_id),
    
    -- BUSINESS RULES:
    -- Monthly Vesting = vested_percentage = (100 / vesting_period_months)
    -- Example: 48-month vest = 2.0833% per month (100/48)
    -- Cliff Effect = First vesting_date >= cliff_date
    -- Cumulative Tracking = Sum of all vested_shares to date
    -- Exercise Window = vesting_date to grant.expiration_date
    
    -- QUERY PATTERNS:
    -- Next Vesting = MIN(vesting_date) WHERE vesting_date > CURRENT_DATE
    -- Vested Amount = SUM(vested_shares) WHERE vesting_date <= CURRENT_DATE
    -- Upcoming Vesting = WHERE vesting_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '90 days'
    
    -- EXAMPLE DATA:
    -- vesting_date='2025-02-01', vested_shares=83, vested_percentage=2.0833, cumulative_vested_shares=83
    -- vesting_date='2025-03-01', vested_shares=83, vested_percentage=2.0833, cumulative_vested_shares=166
    
    INDEX idx_tranche_schedule (tranche_id, vesting_date),
    INDEX idx_vesting_date (vesting_date),
    INDEX idx_vested_status (is_vested, vesting_date),
    INDEX idx_upcoming_vesting (vesting_date) WHERE vesting_date > CURRENT_DATE,
    INDEX idx_exercise_tracking (is_exercised, exercise_date)
);

-- ================================================================
-- SUMMARY OF KEY BUSINESS RULES FOR SQL GENERATION:
-- ================================================================

/*
OFFICER DEFINITION: 
  employee_type IN ('officer', 'executive', 'director', 'ceo', 'cfo', 'cto')

ACTIVE PARTICIPANTS:
  status = 'active' AND (termination_date IS NULL OR termination_date > CURRENT_DATE)

VESTED SHARES:
  SUM(vested_shares) FROM vesting_schedules WHERE vesting_date <= CURRENT_DATE

NEXT VESTING EVENT:
  MIN(vesting_date) FROM vesting_schedules WHERE vesting_date > CURRENT_DATE

EXERCISABLE OPTIONS:
  Vested shares WHERE grant_type = 'option' AND NOT in_blackout_period AND NOT expired

10b5-1 ELIGIBLE:
  Section 16 officer AND last_material_info_date < CURRENT_DATE - INTERVAL '6 months'

IN BLACKOUT PERIOD:
  CURRENT_DATE BETWEEN blackout_start_date AND blackout_end_date

FISCAL QUARTER (Q4 example):
  Based on client.fiscal_year_end, calculate Q4 = 3 months ending on fiscal_year_end

REGIONAL TAX RATES:
  US: 37%, UK: 45%, CA: 33%, Other: 25%
*/
