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
├── schema_info.yaml    ← SchemaManager reads this
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
