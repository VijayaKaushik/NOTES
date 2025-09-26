PHASE 1: FOUNDATION - Schema Section + Business Context

 Phase 1 Deliverables
At the end of Phase 1, you have:

SchemaManager class - Loads and formats database schema documentation
BusinessContextManager class - Loads and provides domain knowledge
YAML schema file - Structured database documentation
Markdown business context file - Domain knowledge documentation
Fallback mechanisms - System works even without files
Integration interface - Clean API for other phases to consume

Phase 1 creates the knowledge foundation that makes all subsequent phases possible.


1. SchemaManager → Technical database documentation
2. BusinessContextManager → Domain knowledge and entity definitions


## Component 1: SchemaManager

Purpose: Provides GPT-4o with comprehensive database structure knowledge so it can generate accurate JOINs, use correct table names, and understand relationships.


Step 1: File Structure Setup
src/rules/prompts/
├── schema_info.yaml /Table _ifo   ← SchemaManager reads this #U(DDL-Only with Rich Comments)
├── business_context.md ← BusinessContextManager reads this
└── base_template.txt



Step 4: Schema Section Output
When get_schema_section() is called, it produces:
markdown### Schema Organization & Data Hierarchy
We have five main schemas: clients, plans, grants, participants, vesting_schedules

**clients schema:**
- `clients.client_latest`: Master client/company information
  - `client_hub_key`: Primary key for joining
  - `client_name`: Company name
  - `fiscal_year_end`: Drives quarterly calculations

**participants schema:**  
- `participants.participant_detail`: Core participant information
  - `participant_hub_key`: Primary key for joining
  - `employee_type`: officer, executive, employee, etc.
  - `status`: active, terminated, etc.
 
## Component 2: BusinessContextManager

Purpose:
Provides GPT-4o with domain knowledge about what entities mean in the equity world, how they relate to each other, and what the business processes are.
Step 1: Business Context File
markdown# src/rules/prompts/business_context.md

## Business Context & Entity Relationships

**Key Entity Definitions:**
- **Clients** = Companies that use Global Shares for equity management
- **Plans** = Structured equity compensation programs (e.g., "2024 Employee Stock Option Plan")
- **Securities** = Types of equity instruments within plans (ISO, NQSO, RSUs, etc.)
- **Grants** = Individual equity awards given to specific participants under a plan
- **Participants** = Employees of client companies who receive equity awards
- **Tranches** = Subdivisions of grants with different vesting terms
- **Vesting Schedules** = Time-based rules governing when equity becomes exercisable

**Business Relationships:**
- One Client → Many Plans (different equity programs)
- One Plan → Many Securities (different equity types available)
- One Plan → Many Grants (individual awards to employees)
- One Grant → One Participant (specific employee recipient)
- One Grant → Many Tranches (different vesting portions)
- One Tranche → One Vesting Schedule (specific timing rules)

**Data Flow:**
1. **Client Setup**: Company establishes relationship with Global Shares
2. **Plan Creation**: Client creates equity compensation plans with securities
3. **Grant Award**: Participants receive grants from specific plan securities
4. **Tranche Definition**: Grants divided into tranches with vesting terms
5. **Vesting Execution**: Schedules determine when tranches become exercisable
6. **Exercise/Settlement**: Participants realize equity value based on vested amounts

### FINAL OUTPUT Phase 1 :

These components get passed to the prompt assembly:
python# Foundation knowledge that GPT-4o receives:
foundation_context = f"""
{schema_section}

{business_context}

[Other phases will add more context here...]


   
