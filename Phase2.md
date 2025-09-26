## Phase 2: Core Logic builds the intelligent reasoning layer on top of Phase 1's foundation:

### BusinessRulesManager → Dynamic vocabulary mappings and business logic
### GenerationRulesManager → SQL generation guidelines and best practices

🚀 Phase 2 Deliverables
At end of Phase 2, you have:

BusinessRulesManager class - Dynamic rule engine with vocabulary mappings
GenerationRulesManager class - SQL generation guidelines
Rule definitions - Core equity business rules (vocabulary, calculations, compliance)
Configuration system - YAML-based rule customization
Context generation - Query-type-aware rule selection
JOIN discovery - Automatic table requirement detection
Priority system - Rule conflict resolution
Caching system - Performance optimization

Phase 2 transforms static schema knowledge into intelligent, context-aware business reasoning that allows GPT-4o to understand your equity domain and generate accurate, business-compliant SQL!


Purpose:
Transforms business terminology into SQL logic dynamically. When user says "officers", it provides employee_type IN ('officer', 'executive', 'director'). When they say "active", it provides the complex active participant logic.
Step 1: Rule Type Classification
pythonclass RuleType(Enum):
    """Categories of business rules"""
    VOCABULARY = "vocabulary"      # Business terms → SQL conditions  
    CALCULATION = "calculation"    # How to compute derived values
    COMPLIANCE = "compliance"      # Regulatory and legal requirements
    TEMPORAL = "temporal"          # Complex date logic
    RELATIONSHIP = "relationship"  # How entities connect
    AGGREGATION = "aggregation"    # How to group and summarize
Step 2: Business Rule Structure
python@dataclass
class BusinessRule:
    """Individual business rule definition"""
    rule_id: str                    # Unique identifier: "vocab_officers"
    rule_type: RuleType            # Which category: VOCABULARY
    name: str                      # Human name: "Officer Definition"
    description: str               # What it does: "Define what constitutes an officer"
    conditions: Dict               # When to apply: {"terms": ["officers", "executives"]}
    sql_template: Optional[str]    # SQL logic: "employee_type IN ('officer', 'executive')"
    requires_joins: List[str]      # Tables needed: ["participants.participant_detail"]
    priority: int = 1              # Conflict resolution: higher wins
Step 3: Core Rules Loading
pythondef _load_core_rules(self):
    """Load essential equity business rules that rarely change"""
    
    # VOCABULARY RULES - Map business terms to SQL
    vocabulary_rules = [
        BusinessRule(
            rule_id="vocab_officers",
            rule_type=RuleType.VOCABULARY,
            name="Officer Definition",
            description="Define what constitutes an officer in equity context",
            conditions={"terms": ["officers", "executives", "leadership"]},
            sql_template="employee_type IN ('officer', 'executive', 'director', 'ceo', 'cfo', 'cto')",
            requires_joins=["participants.participant_detail"]
        ),
        BusinessRule(
            rule_id="vocab_active_participants", 
            rule_type=RuleType.VOCABULARY,
            name="Active Participant Definition",
            description="Define active participants with complex logic",
            conditions={"terms": ["active", "current", "employed"]},
            sql_template="status = 'active' AND (termination_date IS NULL OR termination_date > CURRENT_DATE)",
            requires_joins=["participants.participant_detail"]
        ),
        BusinessRule(
            rule_id="vocab_vested_grants",
            rule_type=RuleType.VOCABULARY, 
            name="Vested Grants Definition",
            description="When grants are considered vested",
            conditions={"terms": ["vested", "available", "exercisable"]},
            sql_template="vs.vesting_date <= CURRENT_DATE",
            requires_joins=["vesting_schedules.vesting_schedules"]
        )
    ]
    
    # CALCULATION RULES - How to compute values
    calculation_rules = [
        BusinessRule(
            rule_id="calc_vested_amount",
            rule_type=RuleType.CALCULATION,
            name="Vested Amount Calculation", 
            description="Calculate vested portion of grant",
            conditions={"calculation": "vested_amount"},
            sql_template="""CASE 
                WHEN vs.vesting_date <= CURRENT_DATE 
                THEN g.grant_amount * (vs.vested_percentage / 100.0)
                ELSE 0 
            END""",
            requires_joins=["grants.grant_latest", "vesting_schedules.vesting_schedules"]
        ),
        BusinessRule(
            rule_id="calc_exercise_value",
            rule_type=RuleType.CALCULATION,
            name="Exercise Value Calculation",
            description="Value of exercising vested options",
            conditions={"calculation": "exercise_value"},
            sql_template="GREATEST(0, (current_stock_price - g.exercise_price) * vested_shares)",
            requires_joins=["grants.grant_latest", "clients.current_valuations"]
        )
    ]
    
    # COMPLIANCE RULES - Regulatory requirements
    compliance_rules = [
        BusinessRule(
            rule_id="comp_section16_officers",
            rule_type=RuleType.COMPLIANCE,
            name="Section 16 Officer Identification",
            description="SEC Section 16 officer definition",
            conditions={"compliance": "section_16"},
            sql_template="(p.employee_type IN ('ceo', 'cfo', 'director') OR pl.ownership_percentage > 10)",
            requires_joins=["participants.participant_detail", "participants.participant_legal_detail"]
        ),
        BusinessRule(
            rule_id="comp_10b51_eligibility",
            rule_type=RuleType.COMPLIANCE,
            name="10b5-1 Plan Eligibility",
            description="Who can participate in 10b5-1 trading plans",
            conditions={"compliance": "10b5-1"},
            sql_template="""p.employee_type IN ('officer', 'executive', 'director')
                           AND NOT EXISTS (
                               SELECT 1 FROM participants.participant_legal_detail pld 
                               WHERE pld.participant_hub_key = p.participant_hub_key
                               AND pld.last_material_info_date > CURRENT_DATE - INTERVAL '6 months'
                           )""",
            requires_joins=["participants.participant_detail", "participants.participant_legal_detail"]
        )
    ]
    
    # Store all rules in manager
    all_rules = vocabulary_rules + calculation_rules + compliance_rules
    for rule in all_rules:
        self.rules[rule.rule_id] = rule
Step 4: Configuration-Based Rules
yaml# config/business_rules.yaml - Customizable rules
rules:
  - id: "custom_senior_officers"
    type: "vocabulary"
    name: "Senior Officer Definition"
    description: "Company-specific definition of senior officers"
    priority: 5  # Overrides default officer definition
    conditions:
      terms: ["senior officers", "c-suite", "executives"]
    sql_template: "employee_type IN ('ceo', 'cfo', 'cto') AND employee_level >= 'VP'"
    requires_joins: ["participants.participant_employer_detail"]
    
  - id: "custom_accelerated_vesting"
    type: "calculation" 
    name: "Accelerated Vesting Calculation"
    description: "Handle acquisition-triggered acceleration"
    conditions:
      calculation: "accelerated_vesting"
    sql_template: |
      CASE 
        WHEN acquisition_date IS NOT NULL AND acquisition_date <= CURRENT_DATE
        THEN g.grant_amount  -- 100% vested on acquisition
        ELSE normal_vested_amount
      END
    requires_joins: ["grants.grant_latest", "clients.corporate_events"]
Step 5: Context-Aware Rule Selection
python@lru_cache(maxsize=100)
def get_rules_context(self, query_type: str = "general") -> str:
    """Get relevant business rules for this specific query type"""
    
    # Step 1: Get rules relevant to query type
    relevant_rules = self._get_relevant_rules(query_type)
    
    # Step 2: Organize by rule type
    context_sections = {
        RuleType.VOCABULARY: "Business Term Mappings:",
        RuleType.CALCULATION: "Calculation Rules:",
        RuleType.COMPLIANCE: "Compliance Rules:",
        RuleType.TEMPORAL: "Date and Time Rules:"
    }
    
    # Step 3: Build formatted context
    context = ""
    for rule_type, section_header in context_sections.items():
        type_rules = [r for r in relevant_rules if r.rule_type == rule_type]
        
        if type_rules:
            context += f"\n{section_header}\n"
            for rule in sorted(type_rules, key=lambda x: x.priority, reverse=True):
                context += f"- {rule.name}: {rule.description}\n"
                if rule.sql_template:
                    context += f"  SQL: {rule.sql_template}\n"
                if rule.requires_joins:
                    context += f"  Requires: {', '.join(rule.requires_joins)}\n"
            context += "\n"
    
    return context

def _get_relevant_rules(self, query_type: str) -> List[BusinessRule]:
    """Smart rule filtering based on query characteristics"""
    
    relevant_rules = []
    
    # Always include vocabulary rules (core translations)
    vocabulary_rules = [r for r in self.rules.values() if r.rule_type == RuleType.VOCABULARY]
    relevant_rules.extend(vocabulary_rules)
    
    # Add query-type specific rules
    if "vesting" in query_type.lower():
        temporal_rules = [r for r in self.rules.values() if r.rule_type == RuleType.TEMPORAL]
        relevant_rules.extend(temporal_rules)
        
    if "compliance" in query_type.lower() or "10b5-1" in query_type.lower():
        compliance_rules = [r for r in self.rules.values() if r.rule_type == RuleType.COMPLIANCE]
        relevant_rules.extend(compliance_rules)
        
    if "calculation" in query_type.lower() or "value" in query_type.lower():
        calc_rules = [r for r in self.rules.values() if r.rule_type == RuleType.CALCULATION]
        relevant_rules.extend(calc_rules)
    
    # Remove duplicates and sort by priority
    seen = set()
    unique_rules = []
    for rule in sorted(relevant_rules, key=lambda x: x.priority, reverse=True):
        if rule.rule_id not in seen:
            unique_rules.append(rule)
            seen.add(rule.rule_id)
    
    return unique_rules
Step 6: JOIN Requirements Discovery
pythondef get_required_joins(self, query_type: str) -> Set[str]:
    """Determine what database tables must be joined"""
    
    relevant_rules = self._get_relevant_rules(query_type)
    
    required_joins = set()
    for rule in relevant_rules:
        if rule.requires_joins:
            required_joins.update(rule.requires_joins)
    
    return required_joins

# Example:
# Query: "Show officers with 10b5-1 plans"
# Returns: {"participants.participant_detail", "participants.participant_legal_detail"}
⚙️ Component 2: GenerationRulesManager
Purpose:
Provides GPT-4o with SQL generation best practices, performance guidelines, and equity-specific query patterns.
Step 1: Generation Rules File Structure
markdown# src/rules/prompts/generation_rules.md

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
11. Always join through proper hierarchy: Clients → Plans → Grants → Participants → Vesting Schedules
12. Apply appropriate filtering for active vs terminated participants
13. Consider fiscal calendar vs calendar year for date-based queries
14. Include proper error handling for division by zero in calculations
15. For regional queries, use participants.participant_address
16. For plan-level analysis, start from clients.client_latest → plans.plans
17. For vesting queries, join through grants.tranches → vesting_schedules.vesting_schedules

**Query Optimization Guidelines:**
18. Use indexes hints when available: INDEX(idx_employee_type)
19. Prefer EXISTS over IN for subqueries when checking existence
20. Use LIMIT appropriately for large result sets
21. Consider using window functions for ranking and running totals
22. Always include ORDER BY for consistent results
Step 2: GenerationRulesManager Implementation
pythonclass GenerationRulesManager:
    """Manages SQL generation guidelines and best practices"""
    
    def __init__(self, rules_file_path: Path = Path("src/rules/prompts/generation_rules.md")):
        self.rules_file_path = rules_file_path
        self.generation_rules = self._load_generation_rules()
    
    def _load_generation_rules(self) -> str:
        """Load generation rules from markdown file"""
        try:
            with open(self.rules_file_path, 'r') as f:
                return f.read()
        except FileNotFoundError:
            logging.warning(f"Generation rules file not found: {self.rules_file_path}")
            return self._get_default_generation_rules()
    
    def get_generation_rules(self) -> str:
        """Get generation rules for prompts"""
        return self.generation_rules
    
    def _get_default_generation_rules(self) -> str:
        """Fallback generation rules"""
        return """
        ## Query Generation Rules:
        1. Always use schema-qualified table names
        2. Use meaningful table aliases  
        3. Join tables using hub_keys
        4. Apply business rules for term definitions
        5. Handle equity-specific date logic
        6. Include all required JOINs from business rules
        7. Handle NULL values appropriately
        8. Use proper hierarchy: Clients → Plans → Grants → Participants
        """
🔄 Phase 2 Integration Process
Step 1: Initialization
python# When system starts up:
business_rules_manager = BusinessRulesManager(db_connection=db_connection)
generation_rules_manager = GenerationRulesManager()

print("🧠 Business Rules Manager initialized with", len(business_rules_manager.rules), "rules")
print("⚙️ Generation Rules Manager initialized")
Step 2: Query Classification
pythondef classify_query_type(query: str) -> str:
    """Classify query to determine which rules are relevant"""
    
    query_lower = query.lower()
    
    if any(word in query_lower for word in ['vesting', 'vest', 'cliff']):
        return 'vesting_query'
    elif any(word in query_lower for word in ['officer', '10b5-1', 'compliance', 'blackout']):
        return 'compliance_query'  
    elif any(word in query_lower for word in ['value', 'exercise', 'tax', 'calculation']):
        return 'calculation_query'
    elif any(word in query_lower for word in ['region', 'country', 'department']):
        return 'regional_query'
    else:
        return 'general_query'
Step 3: Dynamic Context Generation
python# For each query, Phase 2 provides:
query_type = classify_query_type(user_query)

# Get business rules context
rules_context = business_rules_manager.get_rules_context(query_type)

# Get required joins
required_joins = list(business_rules_manager.get_required_joins(query_type))

# Get generation rules
generation_rules = generation_rules_manager.get_generation_rules()
📊 Complete Phase 2 Example
Input: "Show officers with 10b5-1 plans"
Phase 2 Processing:
python# Step 1: Query classification
query_type = classify_query_type("Show officers with 10b5-1 plans")
# Result: 'compliance_query'

# Step 2: Get relevant business rules
rules_context = business_rules_manager.get_rules_context('compliance_query')
# Result:
"""
Business Term Mappings:
- Officer Definition: Define what constitutes an officer
  SQL: employee_type IN ('officer', 'executive', 'director', 'ceo', 'cfo', 'cto')
  Requires: participants.participant_detail

- Active Participant Definition: Define active participants
  SQL: status = 'active' AND (termination_date IS NULL OR termination_date > CURRENT_DATE)  
  Requires: participants.participant_detail

Compliance Rules:
- 10b5-1 Plan Eligibility: Who can participate in 10b5-1 trading plans
  SQL: employee_type IN ('officer', 'executive', 'director') AND NOT EXISTS (...)
  Requires: participants.participant_detail, participants.participant_legal_detail
"""

# Step 3: Get required joins
required_joins = business_rules_manager.get_required_joins('compliance_query')
# Result: {'participants.participant_detail', 'participants.participant_legal_detail'}

# Step 4: Get generation rules
generation_rules = generation_rules_manager.get_generation_rules()
# Result: Complete markdown with SQL best practices
Phase 2 Output to Prompt:
python# Context provided to GPT-4o:
phase2_context = f"""
{rules_context}

{generation_rules}

## Required JOINs for this Query:
{', '.join(required_joins)}

Create SQL for: Show officers with 10b5-1 plans
"""
GPT-4o Understanding (thanks to Phase 2):

✅ Knows "officers" = employee_type IN ('officer', 'executive', 'director', 'ceo', 'cfo', 'cto')
✅ Knows "10b5-1" = check trading_plan_type = '10b5-1' in legal detail table
✅ Knows required JOINs = must include participant_detail and participant_legal_detail
✅ Follows SQL best practices = schema-qualified names, meaningful aliases
✅ Applies compliance logic = includes eligibility checks

🎯 Phase 2 Success Criteria
Phase 2 is successful when:

Business Rules Loaded:

python   assert len(business_rules_manager.rules) > 0
   assert "vocab_officers" in business_rules_manager.rules
   assert business_rules_manager.get_rules_context("compliance_query") != ""

Context Generation Works:

python   context = business_rules_manager.get_rules_context("vesting_query")
   assert "Business Term Mappings:" in context
   assert "vested" in context.lower()

JOIN Discovery Works:

python   joins = business_rules_manager.get_required_joins("compliance_query")
   assert "participants.participant_legal_detail" in joins

Rule Priority System:

python   # Higher priority custom rules override defaults
   custom_rule = BusinessRule(rule_id="custom_officers", priority=10, ...)
   business_rules_manager.add_rule(custom_rule)
   # Custom rule should appear first in context

