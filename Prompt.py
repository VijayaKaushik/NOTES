# ================================
# File: src/rules/prompts/base_template.txt
# ================================
"""You are a PostgreSQL expert specializing in equity plan management systems. 
Given an input question, create a syntactically correct PostgreSQL query to run.

## Database Schema Overview
Here is the relevant table info: {table_info}

{schema_section}

{business_context}

{rules_context}

{discovery_context}

{date_context}

{generation_rules}

## Required JOINs for this Query:
{required_joins}

{query_patterns}

Create the SQL query for: {input_question}

Return only the PostgreSQL query without additional explanation unless complex."""

# ================================
# File: src/rules/prompts/schema_info.yaml
# ================================
organization: |
  We have five main schemas: **clients**, **plans**, **grants**, **participants**, and **vesting_schedules**.
  
  **Hierarchical Data Structure:**
  ```
  Client Company
  ├── Plans (Multiple equity compensation plans)
  │   ├── Securities (Stock classes, option types per plan)  
  │   └── Grants (Individual awards under each plan)
  │       ├── Participants (Employees receiving grants)
  │       └── Tranches (Grant subdivisions with different terms)
  │           └── Vesting Schedules (Time-based release of equity)
  ```

schemas:
  clients:
    client_latest:
      description: "Master client/company information"
      key_columns:
        client_name: "Company name"
        client_hub_key: "Primary key for joining"
        fiscal_year_end: "Company's fiscal year end date"
    
  plans:
    plans:
      description: "Equity compensation plans for each client"
      key_columns:
        plan_id: "Primary key for plan"
        client_hub_key: "Links to clients.client_latest"
        plan_name: "Name of equity plan"
        plan_type: "Type of plan (ESOP, RSU, etc.)"
    
    securities:
      description: "Types of equity instruments available in each plan"
      key_columns:
        security_id: "Primary key for security"
        plan_id: "Links to plans.plans"
        security_type: "Type of equity (ISO, NQSO, RSU, etc.)"

  participants:
    participant_detail:
      description: "Core participant information"  
      key_columns:
        participant_hub_key: "Primary key for joining"
        employee_type: "Job classification (officer, executive, employee, etc.)"
        status: "Employment status (active, terminated, etc.)"
        termination_date: "When employment ended (if applicable)"
    
    participant_employer_detail:
      description: "Employment relationship to clients"
      key_columns:
        participant_hub_key: "Links to participant_detail"
        client_hub_key: "Links to clients.client_latest"
        department: "Employee's department/division"
    
    participant_address:
      description: "Address details"
      key_columns:
        participant_hub_key: "Links to participant_detail"
        country_code: "ISO country code"
        region_code: "Geographic region"
    
    participant_legal_detail:
      description: "Legal/compliance information"
      key_columns:
        participant_hub_key: "Links to participant_detail"
        trading_plan_type: "Type of trading plan (10b5-1, etc.)"
        blackout_start_date: "Trading blackout start"
        blackout_end_date: "Trading blackout end"

  grants:
    grant_latest:
      description: "Individual equity awards"
      key_columns:
        grant_id: "Primary key for grant"
        plan_id: "Links to plans.plans"
        participant_hub_key: "Links to participants.participant_detail"
        security_id: "Links to plans.securities"
        grant_type: "Type of equity (stock_option, rsu, etc.)"
        grant_date: "When grant was awarded"
        grant_amount: "Number of shares/units granted"
    
    tranches:
      description: "Grant subdivisions with different vesting terms"
      key_columns:
        tranche_id: "Primary key for tranche"
        grant_id: "Links to grants.grant_latest"
        tranche_number: "Sequence number (1, 2, 3, etc.)"
        tranche_percentage: "Percentage of total grant"
        cliff_months: "Cliff period in months"

  vesting_schedules:
    vesting_schedules:
      description: "Time-based rules for equity release"
      key_columns:
        schedule_id: "Primary key for schedule"
        tranche_id: "Links to grants.tranches"
        vesting_date: "When shares vest"
        vested_percentage: "Percentage that vests on this date"
        vesting_type: "Type of vesting (time_based, performance, etc.)"

# ================================  
# File: src/rules/prompts/business_context.md
# ================================
## Business Context & Entity Relationships

**Key Entity Definitions:**
- **Clients** = Companies that use Global Shares for equity management
- **Plans** = Structured equity compensation programs (e.g., "2024 Employee Stock Option Plan")
- **Securities** = Types of equity instruments within plans (Common Stock, ISO, NQSO, RSUs, etc.)
- **Grants** = Individual equity awards given to specific participants under a plan
- **Participants** = Employees of client companies who receive equity awards
- **Tranches** = Subdivisions of grants with different vesting terms (e.g., 25% per year over 4 years)
- **Vesting Schedules** = Time-based rules governing when equity becomes exercisable/owned

**Business Relationships:**
- One Client → Many Plans (different equity programs)
- One Plan → Many Securities (different equity types available)  
- One Plan → Many Grants (individual awards to employees)
- One Grant → One Participant (specific employee recipient)
- One Grant → Many Tranches (different vesting portions)
- One Tranche → One Vesting Schedule (specific timing rules)

**Data Flow:**
1. **Client Setup**: Company establishes relationship with Global Shares
2. **Plan Creation**: Client creates equity compensation plans with available securities
3. **Grant Award**: Individual participants receive grants from specific plan securities  
4. **Tranche Definition**: Grants are divided into tranches with different vesting terms
5. **Vesting Schedule Creation**: Each tranche gets specific vesting schedule rules
6. **Vesting Execution**: Schedules determine when tranches become exercisable/owned
7. **Exercise/Settlement**: Participants realize equity value based on vested amounts

# ================================
# File: src/rules/prompts/generation_rules.md  
# ================================
## Query Generation Rules:

**Core Rules:**
1. Always use schema-qualified table names (e.g., `clients.client_latest`)
2. Use meaningful table aliases (e.g., `c` for client, `p` for participant, `g` for grant)
3. Join tables using hub_keys and proper foreign key relationships
4. Apply business rules from the context above for term definitions
5. Handle equity-specific date logic using the date context provided

**Performance Rules:**
6. Use discovered entity mappings from discovery context when provided
7. Include all required JOINs as specified in business rules
8. Handle NULL values appropriately (use COALESCE, IS NULL checks)
9. Consider performance implications (use appropriate WHERE clause ordering)
10. Use CTEs for complex queries involving multiple aggregations

**Domain-Specific Rules:**
11. Always join through the proper hierarchy: Clients → Plans → Grants → Participants → Tranches → Vesting Schedules
12. Apply appropriate filtering for active vs terminated participants
13. Consider fiscal calendar vs calendar year for date-based queries
14. Include proper error handling for division by zero in calculations
15. For regional queries, use participants.participant_address or participants.participant_employer_detail tables
16. For plan-level analysis, start from clients.client_latest → plans.plans → grants.grant_latest
17. For vesting queries, join through grants.tranches → vesting_schedules.vesting_schedules

# ================================
# File: src/rules/prompts/query_patterns.md
# ================================
## Common Query Patterns:

**Vesting Queries:**
```sql
-- Pattern: Join grants → tranches → vesting_schedules
FROM grants.grant_latest g
JOIN grants.tranches t ON g.grant_id = t.grant_id  
JOIN vesting_schedules.vesting_schedules vs ON t.tranche_id = vs.tranche_id
WHERE vs.vesting_date BETWEEN [date_range]
```

**Compliance Queries:**
```sql
-- Pattern: Include legal detail tables, apply officer/insider definitions  
FROM participants.participant_detail p
JOIN participants.participant_legal_detail pl ON p.participant_hub_key = pl.participant_hub_key
WHERE p.employee_type IN [officer_types] AND pl.trading_plan_type = '10b5-1'
```

**Plan-Level Analysis:**
```sql  
-- Pattern: Start from client → plans → grants hierarchy
FROM clients.client_latest c
JOIN plans.plans pl ON c.client_hub_key = pl.client_hub_key
JOIN grants.grant_latest g ON pl.plan_id = g.plan_id
```

**Regional Breakdowns:**
```sql
-- Pattern: Use participant_address, apply geographic entity mappings
FROM participants.participant_detail p
JOIN participants.participant_address pa ON p.participant_hub_key = pa.participant_hub_key
GROUP BY pa.region_code, pa.country_code
```

# ================================
# File: src/rules/prompts/examples.yaml
# ================================
examples:
  - input: "Show all active participants"
    expected_sql: |
      SELECT p.participant_name, p.employee_type
      FROM participants.participant_detail p
      WHERE p.status = 'active' 
      AND (p.termination_date IS NULL OR p.termination_date > CURRENT_DATE)
    
  - input: "Find officers with vesting in next month"
    expected_sql: |
      SELECT p.participant_name, vs.vesting_date, vs.vested_percentage
      FROM participants.participant_detail p
      JOIN grants.grant_latest g ON p.participant_hub_key = g.participant_hub_key
      JOIN grants.tranches t ON g.grant_id = t.grant_id
      JOIN vesting_schedules.vesting_schedules vs ON t.tranche_id = vs.tranche_id
      WHERE p.employee_type IN ('officer', 'executive', 'director')
      AND vs.vesting_date >= DATE_TRUNC('month', CURRENT_DATE + INTERVAL '1 month')
      AND vs.vesting_date < DATE_TRUNC('month', CURRENT_DATE + INTERVAL '2 months')

  - input: "Participants by region with grant counts"  
    expected_sql: |
      SELECT 
        pa.region_code,
        COUNT(DISTINCT p.participant_hub_key) as participant_count,
        COUNT(g.grant_id) as grant_count
      FROM participants.participant_detail p
      JOIN participants.participant_address pa ON p.participant_hub_key = pa.participant_hub_key
      LEFT JOIN grants.grant_latest g ON p.participant_hub_key = g.participant_hub_key
      WHERE p.status = 'active'
      GROUP BY pa.region_code
      ORDER BY participant_count DESC

# ================================
# File: src/rules/prompts/vocabulary_mappings.yaml
# ================================
mappings:
  officer_types:
    - officer
    - executive  
    - director
    - ceo
    - cfo
    - cto
    
  active_status:
    - active
    - employed
    - current
    
  equity_types:
    stock_options:
      - ISO
      - NQSO
      - stock_option
    restricted_stock:
      - RSU  
      - RSA
      - restricted_stock
    
  compliance_plans:
    - 10b5-1
    - trading_plan
    - insider_plan

geographic_regions:
  us_variants:
    - US
    - USA
    - United States
    - U.S.
    - U.S.A.
  uk_variants: 
    - UK
    - United Kingdom
    - Britain
    - Great Britain
