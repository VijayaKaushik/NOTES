# ================================================================
# COMPLETE EQUITY QUERY ENGINE IMPLEMENTATION
# Phases 1-5: From Foundation to Full Integration
# ================================================================

import os
import re
import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Set, Union, Any
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache
import logging
from datetime import datetime, date, timedelta
import asyncio
import psycopg2
import openai
from pydantic import BaseModel, Field

# ================================================================
# PHASE 1: FOUNDATION - Schema Section + Business Context
# ================================================================

class SchemaManager:
    """Handles database schema documentation and context"""
    
    def __init__(self, schema_file_path: Path = Path("src/rules/prompts/schema_info.yaml")):
        self.schema_file_path = schema_file_path
        self.schema_data = self._load_schema_data()
    
    def _load_schema_data(self) -> Dict:
        """Load schema information from YAML file"""
        try:
            with open(self.schema_file_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logging.warning(f"Schema file not found: {self.schema_file_path}")
            return self._get_default_schema()
    
    def _get_default_schema(self) -> Dict:
        """Default schema structure if file not found"""
        return {
            'organization': """
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
            """,
            'schemas': {
                'clients': {
                    'client_latest': {
                        'description': 'Master client/company information',
                        'key_columns': {
                            'client_hub_key': 'Primary key for joining',
                            'client_name': 'Company name',
                            'fiscal_year_end': 'Company fiscal year end date'
                        }
                    }
                },
                'participants': {
                    'participant_detail': {
                        'description': 'Core participant information',
                        'key_columns': {
                            'participant_hub_key': 'Primary key for joining',
                            'employee_type': 'Job classification (officer, executive, employee, etc.)',
                            'status': 'Employment status (active, terminated, etc.)'
                        }
                    }
                },
                'grants': {
                    'grant_latest': {
                        'description': 'Individual equity awards',
                        'key_columns': {
                            'grant_id': 'Primary key for grant',
                            'participant_hub_key': 'Links to participants',
                            'plan_id': 'Links to plans'
                        }
                    }
                }
            }
        }
    
    def get_schema_section(self) -> str:
        """Build complete schema section for prompts"""
        schema_data = self.schema_data
        sections = []
        
        # Organization overview
        if 'organization' in schema_data:
            sections.append("### Schema Organization & Data Hierarchy")
            sections.append(schema_data['organization'])
        
        # Schema details
        if 'schemas' in schema_data:
            sections.append("### Schema Details:")
            for schema_name, schema_info in schema_data['schemas'].items():
                sections.append(f"\n**{schema_name} schema:**")
                for table_name, table_info in schema_info.items():
                    sections.append(f"- `{schema_name}.{table_name}`: {table_info['description']}")
                    if 'key_columns' in table_info:
                        for col, desc in table_info['key_columns'].items():
                            sections.append(f"  - `{col}`: {desc}")
        
        return "\n".join(sections)


class BusinessContextManager:
    """Handles business context and domain knowledge"""
    
    def __init__(self, context_file_path: Path = Path("src/rules/prompts/business_context.md")):
        self.context_file_path = context_file_path
        self.business_context = self._load_business_context()
    
    def _load_business_context(self) -> str:
        """Load business context from markdown file"""
        try:
            with open(self.context_file_path, 'r') as f:
                return f.read()
        except FileNotFoundError:
            logging.warning(f"Business context file not found: {self.context_file_path}")
            return self._get_default_business_context()
    
    def _get_default_business_context(self) -> str:
        """Default business context if file not found"""
        return """
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
        """
    
    def get_business_context(self) -> str:
        """Get business context for prompts"""
        return self.business_context


# ================================================================
# PHASE 2: CORE LOGIC - Rules Context + Generation Rules
# ================================================================

class RuleType(Enum):
    """Types of business rules"""
    VOCABULARY = "vocabulary"
    CALCULATION = "calculation"
    TEMPORAL = "temporal"
    COMPLIANCE = "compliance"
    RELATIONSHIP = "relationship"
    AGGREGATION = "aggregation"


@dataclass
class BusinessRule:
    """Individual business rule definition"""
    rule_id: str
    rule_type: RuleType
    name: str
    description: str
    conditions: Dict
    sql_template: Optional[str] = None
    requires_joins: Optional[List[str]] = None
    priority: int = 1


class BusinessRulesManager:
    """Centralized business rules management for equity domain"""
    
    def __init__(self, db_connection: Optional[Any] = None):
        self.db = db_connection
        self.rules: Dict[str, BusinessRule] = {}
        self.rule_cache = {}
        self._load_all_rules()
    
    def _load_all_rules(self):
        """Load all business rules from various sources"""
        try:
            self._load_core_rules()
            self._load_config_rules()
            logging.info(f"Loaded {len(self.rules)} business rules")
        except Exception as e:
            logging.error(f"Failed to load business rules: {e}")
            self._load_fallback_rules()
    
    def _load_core_rules(self):
        """Load core equity business rules"""
        
        # Vocabulary Rules
        vocabulary_rules = [
            BusinessRule(
                rule_id="vocab_officers",
                rule_type=RuleType.VOCABULARY,
                name="Officer Definition",
                description="Define what constitutes an officer",
                conditions={"terms": ["officers", "executives", "leadership"]},
                sql_template="employee_type IN ('officer', 'executive', 'director', 'ceo', 'cfo', 'cto')"
            ),
            BusinessRule(
                rule_id="vocab_active_participants",
                rule_type=RuleType.VOCABULARY,
                name="Active Participant Definition",
                description="Define active participants",
                conditions={"terms": ["active", "current", "employed"]},
                sql_template="status = 'active' AND (termination_date IS NULL OR termination_date > CURRENT_DATE)"
            ),
            BusinessRule(
                rule_id="vocab_vested_grants",
                rule_type=RuleType.VOCABULARY,
                name="Vested Grants Definition",
                description="Define when grants are considered vested",
                conditions={"terms": ["vested", "available"]},
                sql_template="vesting_date <= CURRENT_DATE",
                requires_joins=["vesting_schedules.vesting_schedules"]
            )
        ]
        
        # Calculation Rules
        calculation_rules = [
            BusinessRule(
                rule_id="calc_vested_amount",
                rule_type=RuleType.CALCULATION,
                name="Vested Amount Calculation",
                description="Calculate vested portion of grant",
                conditions={"calculation": "vested_amount"},
                sql_template="""CASE 
                    WHEN vs.vesting_date <= CURRENT_DATE THEN g.grant_amount * (vs.vested_percentage / 100.0)
                    ELSE 0 
                END""",
                requires_joins=["grants.grant_latest", "vesting_schedules.vesting_schedules"]
            )
        ]
        
        # Compliance Rules
        compliance_rules = [
            BusinessRule(
                rule_id="comp_section16_officers",
                rule_type=RuleType.COMPLIANCE,
                name="Section 16 Officer Identification",
                description="Identify officers subject to Section 16 reporting",
                conditions={"compliance": "section_16"},
                sql_template="(employee_type IN ('ceo', 'cfo', 'director') OR ownership_percentage > 10)",
                requires_joins=["participants.participant_legal_detail"]
            )
        ]
        
        # Store all rules
        all_rules = vocabulary_rules + calculation_rules + compliance_rules
        for rule in all_rules:
            self.rules[rule.rule_id] = rule
    
    def _load_config_rules(self):
        """Load rules from configuration files"""
        config_path = Path("config/business_rules.yaml")
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config_rules = yaml.safe_load(f)
                
                for rule_data in config_rules.get('rules', []):
                    rule = BusinessRule(
                        rule_id=rule_data['id'],
                        rule_type=RuleType(rule_data['type']),
                        name=rule_data['name'],
                        description=rule_data['description'],
                        conditions=rule_data['conditions'],
                        sql_template=rule_data.get('sql_template'),
                        requires_joins=rule_data.get('requires_joins', []),
                        priority=rule_data.get('priority', 1)
                    )
                    self.rules[rule.rule_id] = rule
            except Exception as e:
                logging.error(f"Failed to load config rules: {e}")
    
    def _load_fallback_rules(self):
        """Load minimal fallback rules"""
        fallback = BusinessRule(
            rule_id="fallback_basic",
            rule_type=RuleType.VOCABULARY,
            name="Basic Fallback",
            description="Minimal rules for basic functionality",
            conditions={"terms": ["participants"]},
            sql_template="1=1"
        )
        self.rules[fallback.rule_id] = fallback
    
    @lru_cache(maxsize=100)
    def get_rules_context(self, query_type: str = "general") -> str:
        """Get relevant business rules context for SQL generation"""
        relevant_rules = self._get_relevant_rules(query_type)
        
        context_sections = {
            RuleType.VOCABULARY: "Business Term Mappings:",
            RuleType.CALCULATION: "Calculation Rules:",
            RuleType.COMPLIANCE: "Compliance Rules:",
            RuleType.TEMPORAL: "Date and Time Rules:"
        }
        
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
        """Filter rules based on query type"""
        relevant_rules = []
        
        # Always include vocabulary rules
        vocabulary_rules = [r for r in self.rules.values() if r.rule_type == RuleType.VOCABULARY]
        relevant_rules.extend(vocabulary_rules)
        
        # Add query-type specific rules
        if "compliance" in query_type.lower():
            compliance_rules = [r for r in self.rules.values() if r.rule_type == RuleType.COMPLIANCE]
            relevant_rules.extend(compliance_rules)
        
        if "calculation" in query_type.lower():
            calc_rules = [r for r in self.rules.values() if r.rule_type == RuleType.CALCULATION]
            relevant_rules.extend(calc_rules)
        
        return relevant_rules
    
    def get_required_joins(self, query_type: str) -> Set[str]:
        """Get all table joins required for a query type"""
        relevant_rules = self._get_relevant_rules(query_type)
        
        required_joins = set()
        for rule in relevant_rules:
            if rule.requires_joins:
                required_joins.update(rule.requires_joins)
        
        return required_joins


class GenerationRulesManager:
    """Handles SQL generation rules and guidelines"""
    
    def __init__(self, rules_file_path: Path = Path("src/rules/prompts/generation_rules.md")):
        self.rules_file_path = rules_file_path
        self.generation_rules = self._load_generation_rules()
    
    def _load_generation_rules(self) -> str:
        """Load generation rules from file"""
        try:
            with open(self.rules_file_path, 'r') as f:
                return f.read()
        except FileNotFoundError:
            return self._get_default_generation_rules()
    
    def _get_default_generation_rules(self) -> str:
        """Default generation rules"""
        return """
        ## Query Generation Rules:
        1. Always use schema-qualified table names (e.g., `clients.client_latest`)
        2. Use meaningful table aliases (e.g., `c` for client, `p` for participant, `g` for grant)
        3. Join tables using hub_keys and proper foreign key relationships
        4. Apply business rules from the context above for term definitions
        5. Handle equity-specific date logic using the date context provided
        6. Use discovered entity mappings from discovery context when provided
        7. Include all required JOINs as specified in business rules
        8. Handle NULL values appropriately (use COALESCE, IS NULL checks)
        9. Consider performance implications (use appropriate WHERE clause ordering)
        10. Always join through proper hierarchy: Clients → Plans → Grants → Participants → Vesting Schedules
        """
    
    def get_generation_rules(self) -> str:
        """Get generation rules for prompts"""
        return self.generation_rules


# ================================================================
# PHASE 3: INTELLIGENCE - Discovery Context + Date Context
# ================================================================

class EntityDiscovery:
    """Discovers data variations and provides mapping context"""
    
    def __init__(self, db_connection: Optional[Any] = None, openai_client: Optional[Any] = None):
        self.db = db_connection
        self.openai_client = openai_client
        self.discovery_cache = {}
        self.common_mappings = self._load_common_mappings()
    
    def _load_common_mappings(self) -> Dict:
        """Load common entity mappings"""
        return {
            'country': {
                'US': ['US', 'USA', 'United States', 'U.S.', 'U.S.A.'],
                'UK': ['UK', 'United Kingdom', 'Britain', 'Great Britain'],
                'Germany': ['Germany', 'Deutschland', 'DE']
            },
            'employee_type': {
                'officers': ['officer', 'executive', 'director', 'ceo', 'cfo', 'cto'],
                'active': ['active', 'employed', 'current']
            }
        }
    
    async def discover_entities(self, user_query: str) -> str:
        """Main entry point for entity discovery"""
        entities = self._extract_discoverable_entities(user_query)
        
        if not entities:
            return ""
        
        discovery_results = {}
        for entity in entities:
            discovery_results[entity['value']] = await self._discover_entity_variations(entity)
        
        return self._build_discovery_context(discovery_results)
    
    def _extract_discoverable_entities(self, query: str) -> List[Dict]:
        """Extract entities that need discovery"""
        entities = []
        
        # Geographic entities
        geo_patterns = [r'\b(US|UK|Germany|region|country)\b']
        for pattern in geo_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            for match in matches:
                entities.append({
                    'type': 'country',
                    'value': match.upper(),
                    'table': 'participants.participant_address',
                    'column': 'country_code'
                })
        
        # Employee type entities
        emp_patterns = [r'\b(officers?|executives?|active|terminated)\b']
        for pattern in emp_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            for match in matches:
                entities.append({
                    'type': 'employee_type',
                    'value': match.lower(),
                    'table': 'participants.participant_detail',
                    'column': 'employee_type'
                })
        
        return entities
    
    async def _discover_entity_variations(self, entity: Dict) -> Dict:
        """Discover variations for a specific entity"""
        # Check common mappings first
        entity_type = entity['type']
        entity_value = entity['value']
        
        if entity_type in self.common_mappings and entity_value in self.common_mappings[entity_type]:
            return {
                'exact_matches': self.common_mappings[entity_type][entity_value],
                'confidence': 'high',
                'source': 'common_mappings'
            }
        
        # If database available, query for variations
        if self.db:
            return await self._query_database_variations(entity)
        
        # Fallback to common sense mappings
        return self._fallback_mappings(entity)
    
    async def _query_database_variations(self, entity: Dict) -> Dict:
        """Query database for entity variations"""
        table = entity['table']
        column = entity['column']
        
        try:
            query = f"""
            SELECT DISTINCT {column}, COUNT(*) as count
            FROM {table} 
            WHERE {column} IS NOT NULL 
            GROUP BY {column}
            ORDER BY COUNT(*) DESC
            LIMIT 20;
            """
            
            # Execute query (placeholder - implement actual DB connection)
            # results = await self.db.execute(query)
            # For now, return mock results
            
            return {
                'exact_matches': ['US', 'USA', 'United States'],
                'confidence': 'high',
                'source': 'database_discovery'
            }
            
        except Exception as e:
            logging.error(f"Database discovery failed: {e}")
            return self._fallback_mappings(entity)
    
    def _fallback_mappings(self, entity: Dict) -> Dict:
        """Fallback mappings when other methods fail"""
        return {
            'exact_matches': [entity['value']],
            'confidence': 'low',
            'source': 'fallback'
        }
    
    def _build_discovery_context(self, discovery_results: Dict) -> str:
        """Build discovery context for prompts"""
        if not discovery_results:
            return ""
        
        context = "\nEntity Discovery Context:\n"
        for entity_value, matches in discovery_results.items():
            context += f"For \"{entity_value}\": "
            if matches.get('exact_matches'):
                context += f"Exact matches: {matches['exact_matches']}\n"
            context += f"Confidence: {matches.get('confidence', 'medium')}\n"
        
        return context


class DateProcessor:
    """Processes complex date expressions and provides SQL context"""
    
    def __init__(self, db_connection: Optional[Any] = None):
        self.db = db_connection
        self.fiscal_cache = {}
    
    async def process_dates(self, user_query: str) -> str:
        """Main entry point for date processing"""
        date_expressions = self._extract_date_expressions(user_query)
        
        if not date_expressions:
            return ""
        
        resolved_dates = {}
        for expr in date_expressions:
            resolved_dates[expr['text']] = await self._resolve_date_expression(expr)
        
        return self._build_date_context(resolved_dates)
    
    def _extract_date_expressions(self, query: str) -> List[Dict]:
        """Extract date expressions from query"""
        expressions = []
        
        # Fiscal periods
        fiscal_patterns = [r'\b(Q[1-4]|fiscal|FY)\b']
        for pattern in fiscal_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            for match in matches:
                expressions.append({
                    'text': match,
                    'type': 'fiscal',
                    'context': 'quarterly'
                })
        
        # Relative dates
        relative_patterns = [r'\b(next month|last quarter|upcoming|year-end)\b']
        for pattern in relative_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            for match in matches:
                expressions.append({
                    'text': match,
                    'type': 'relative',
                    'context': 'general'
                })
        
        # Business dates
        business_patterns = [r'\b(next vesting|cliff|exercise window)\b']
        for pattern in business_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            for match in matches:
                expressions.append({
                    'text': match,
                    'type': 'business',
                    'context': 'equity'
                })
        
        return expressions
    
    async def _resolve_date_expression(self, expression: Dict) -> Dict:
        """Resolve individual date expression"""
        expr_type = expression['type']
        expr_text = expression['text'].lower()
        
        if expr_type == 'fiscal':
            return await self._resolve_fiscal_date(expression)
        elif expr_type == 'relative':
            return self._resolve_relative_date(expression)
        elif expr_type == 'business':
            return self._resolve_business_date(expression)
        
        return {'sql': expr_text, 'description': f'Unresolved: {expr_text}'}
    
    async def _resolve_fiscal_date(self, expression: Dict) -> Dict:
        """Resolve fiscal date expressions"""
        expr_text = expression['text'].lower()
        
        # Get fiscal calendar
        fiscal_info = await self._get_fiscal_calendar()
        
        if 'q4' in expr_text:
            # Calculate Q4 based on fiscal year end
            fy_end = fiscal_info.get('fy_end', '2024-12-31')
            # Q4 is the last quarter of fiscal year
            return {
                'sql': f"BETWEEN DATE_TRUNC('quarter', '{fy_end}'::DATE - INTERVAL '3 months') AND '{fy_end}'::DATE",
                'range_start': f"DATE_TRUNC('quarter', '{fy_end}'::DATE - INTERVAL '3 months')",
                'range_end': f"'{fy_end}'::DATE",
                'description': f'Q4 of fiscal year ending {fy_end}',
                'requires_joins': ['clients.client_latest']
            }
        
        return {'sql': expr_text, 'description': f'Fiscal date: {expr_text}'}
    
    def _resolve_relative_date(self, expression: Dict) -> Dict:
        """Resolve relative date expressions"""
        expr_text = expression['text'].lower()
        
        relative_mappings = {
            'next month': {
                'sql': "DATE_TRUNC('month', CURRENT_DATE + INTERVAL '1 month')",
                'range_start': "DATE_TRUNC('month', CURRENT_DATE + INTERVAL '1 month')",
                'range_end': "DATE_TRUNC('month', CURRENT_DATE + INTERVAL '2 months') - INTERVAL '1 day'",
                'description': 'Next calendar month'
            },
            'upcoming': {
                'sql': "CURRENT_DATE + INTERVAL '90 days'",
                'range_start': "CURRENT_DATE",
                'range_end': "CURRENT_DATE + INTERVAL '90 days'",
                'description': 'Next 90 days'
            },
            'year-end': {
                'sql': "DATE_TRUNC('year', CURRENT_DATE + INTERVAL '1 year') - INTERVAL '1 day'",
                'description': 'December 31st of current year'
            }
        }
        
        return relative_mappings.get(expr_text, {
            'sql': expr_text,
            'description': f'Relative date: {expr_text}'
        })
    
    def _resolve_business_date(self, expression: Dict) -> Dict:
        """Resolve business-specific date expressions"""
        expr_text = expression['text'].lower()
        
        if 'next vesting' in expr_text:
            return {
                'sql': "(SELECT MIN(vesting_date) FROM vesting_schedules.vesting_schedules WHERE vesting_date > CURRENT_DATE)",
                'description': 'Next upcoming vesting event',
                'requires_joins': ['vesting_schedules.vesting_schedules']
            }
        elif 'cliff' in expr_text:
            return {
                'sql': "g.grant_date + (t.cliff_months * INTERVAL '1 month')",
                'description': 'Grant cliff dates',
                'requires_joins': ['grants.grant_latest', 'grants.tranches']
            }
        
        return {'sql': expr_text, 'description': f'Business date: {expr_text}'}
    
    async def _get_fiscal_calendar(self) -> Dict:
        """Get fiscal calendar information"""
        # Try to get from cache first
        if 'default' in self.fiscal_cache:
            return self.fiscal_cache['default']
        
        # If database available, query fiscal calendar
        if self.db:
            try:
                # Mock query - implement actual DB connection
                fiscal_info = {
                    'fy_end': '2024-12-31',
                    'fy_start': '2024-01-01',
                    'type': 'calendar'
                }
                self.fiscal_cache['default'] = fiscal_info
                return fiscal_info
            except Exception:
                pass
        
        # Default to calendar year
        default_fiscal = {
            'fy_end': '2024-12-31',
            'fy_start': '2024-01-01',
            'type': 'calendar'
        }
        self.fiscal_cache['default'] = default_fiscal
        return default_fiscal
    
    def _build_date_context(self, resolved_dates: Dict) -> str:
        """Build date context for prompts"""
        if not resolved_dates:
            return ""
        
        context = "\nDate Processing Context:\n"
        required_joins = set()
        
        for original_expr, resolution in resolved_dates.items():
            context += f"- '{original_expr}' → {resolution.get('sql', 'N/A')}\n"
            context += f"  Description: {resolution.get('description', 'No description')}\n"
            
            if 'requires_joins' in resolution:
                required_joins.update(resolution['requires_joins'])
        
        if required_joins:
            context += f"\nRequired JOINs for dates: {list(required_joins)}\n"
        
        return context


# ================================================================
# PHASE 4: OPTIMIZATION - Required Joins + Query Patterns
# ================================================================

class QueryPatterns:
    """Manages common SQL query patterns"""
    
    def __init__(self, patterns_file_path: Path = Path("src/rules/prompts/query_patterns.md")):
        self.patterns_file_path = patterns_file_path
        self.query_patterns = self._load_query_patterns()
    
    def _load_query_patterns(self) -> str:
        """Load query patterns from file"""
        try:
            with open(self.patterns_file_path, 'r') as f:
                return f.read()
        except FileNotFoundError:
            return self._get_default_query_patterns()
    
    def _get_default_query_patterns(self) -> str:
        """Default query patterns"""
        return """
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

        **Regional Breakdowns:**
        ```sql
        -- Pattern: Use participant_address, apply geographic entity mappings
        FROM participants.participant_detail p
        JOIN participants.participant_address pa ON p.participant_hub_key = pa.participant_hub_key
        GROUP BY pa.region_code, pa.country_code
        ```
        """
    
    def get_query_patterns(self) -> str:
        """Get query patterns for prompts"""
        return self.query_patterns


# ================================================================
# PHASE 5: INTEGRATION - PromptManager Assembly
# ================================================================

class QueryClassifier:
    """Classifies queries to determine processing strategy"""
    
    @staticmethod
    def classify_query_type(query: str) -> str:
        """Classify query type for rule selection"""
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
    
    @staticmethod
    def needs_entity_discovery(query: str) -> bool:
        """Check if query needs entity discovery"""
        discovery_triggers = ['US', 'UK', 'region', 'country', 'department', 'IT', 'HR']
        return any(trigger.lower() in query.lower() for trigger in discovery_triggers)
    
    @staticmethod
    def needs_date_processing(query: str) -> bool:
        """Check if query needs date processing"""
        date_triggers = ['Q1', 'Q2', 'Q3', 'Q4', 'next month', 'last quarter', 'fiscal', 'year-end', 'upcoming']
        return any(trigger.lower() in query.lower() for trigger in date_triggers)


class PromptManager:
    """Main prompt assembly and management system"""
    
    def __init__(self, 
                 prompt_dir: Path = Path("src/rules/prompts"),
                 db_connection: Optional[Any] = None,
                 openai_client: Optional[Any] = None):
        self.prompt_dir = prompt_dir
        self.db_connection = db_connection
        self.openai_client = openai_client
        
        # Initialize all components
        self.schema_manager = SchemaManager()
        self.business_context_manager = BusinessContextManager()
        self.business_rules_manager = BusinessRulesManager(db_connection)
        self.entity_discovery = EntityDiscovery(db_connection, openai_client)
        self.date_processor = DateProcessor(db_connection)
        self.generation_rules_manager = GenerationRulesManager()
        self.query_patterns = QueryPatterns()
        
        # Load base template
        self.base_template = self._load_base_template()
    
    def _load_base_template(self) -> str:
        """Load base prompt template"""
        base_template_path = self.prompt_dir / "base_template.txt"
        try:
            with open(base_template_path, 'r') as f:
                return f.read()
        except FileNotFoundError:
            return self._get_default_base_template()
    
    def _get_default_base_template(self) -> str:
        """Default base template"""
        return """You are a PostgreSQL expert specializing in equity plan management systems. 
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

Return only the PostgreSQL query without additional explanation unless the query is complex enough to warrant clarification."""
    
    async def build_complete_prompt(self,
                                  table_info: str,
                                  input_question: str,
                                  additional_context: Optional[Dict] = None) -> str:
        """Build complete prompt with all components"""
        
        # Classify query to determine processing strategy
        query_type = QueryClassifier.classify_query_type(input_question)
        
        # Get static components
        schema_section = self.schema_manager.get_schema_section()
        business_context = self.business_context_manager.get_business_context()
        generation_rules = self.generation_rules_manager.get_generation_rules()
        query_patterns = self.query_patterns.get_query_patterns()
        
        # Get dynamic business rules context
        rules_context = self.business_rules_manager.get_rules_context(query_type)
        required_joins = list(self.business_rules_manager.get_required_joins(query_type))
        
        # Get discovery context if needed
        discovery_context = ""
        if QueryClassifier.needs_entity_discovery(input_question):
            discovery_context = await self.entity_discovery.discover_entities(input_question)
        
        # Get date context if needed
        date_context = ""
        if QueryClassifier.needs_date_processing(input_question):
            date_context = await self.date_processor.process_dates(input_question)
        
        # Assemble complete prompt
        complete_prompt = self.base_template.format(
            table_info=table_info,
            schema_section=schema_section,
            business_context=business_context,
            rules_context=rules_context,
            discovery_context=discovery_context,
            date_context=date_context,
            generation_rules=generation_rules,
            required_joins=', '.join(required_joins) if required_joins else 'None specified',
            query_patterns=query_patterns,
            input_question=input_question
        )
        
        return complete_prompt


# ================================================================
# MAIN QUERY PROCESSOR - INTEGRATION OF ALL PHASES
# ================================================================

class EquityQueryProcessor:
    """Main query processing orchestrator"""
    
    def __init__(self, 
                 db_connection: Optional[Any] = None,
                 openai_client: Optional[Any] = None,
                 config: Optional[Dict] = None):
        self.db_connection = db_connection
        self.openai_client = openai_client
        self.config = config or {}
        
        # Initialize prompt manager with all components
        self.prompt_manager = PromptManager(
            db_connection=db_connection,
            openai_client=openai_client
        )
        
        self.logger = logging.getLogger(__name__)
    
    async def process_query(self, 
                          user_query: str,
                          table_info: str,
                          additional_context: Optional[Dict] = None) -> Dict:
        """Main query processing entry point"""
        
        self.logger.info(f"Processing query: {user_query}")
        
        try:
            # Build complete prompt using all components
            enhanced_prompt = await self.prompt_manager.build_complete_prompt(
                table_info=table_info,
                input_question=user_query,
                additional_context=additional_context
            )
            
            # Generate SQL using GPT-4o (if available)
            sql_result = await self._generate_sql(enhanced_prompt)
            
            # Return comprehensive result
            return {
                'sql': sql_result,
                'enhanced_prompt': enhanced_prompt,
                'query_type': QueryClassifier.classify_query_type(user_query),
                'entity_discovery_used': QueryClassifier.needs_entity_discovery(user_query),
                'date_processing_used': QueryClassifier.needs_date_processing(user_query),
                'success': True
            }
            
        except Exception as e:
            self.logger.error(f"Error processing query: {e}")
            return {
                'sql': None,
                'error': str(e),
                'success': False
            }
    
    async def _generate_sql(self, prompt: str) -> str:
        """Generate SQL using OpenAI GPT-4o"""
        if not self.openai_client:
            # Return placeholder if no OpenAI client
            return "-- SQL would be generated here using GPT-4o with the enhanced prompt"
        
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=4000,
                temperature=0.1
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            self.logger.error(f"OpenAI API call failed: {e}")
            raise


# ================================================================
# EXAMPLE USAGE AND TESTING
# ================================================================

async def main():
    """Example usage of the complete equity query engine"""
    
    # Initialize the query processor
    processor = EquityQueryProcessor()
    
    # Sample table info (this would come from your actual database schema)
    table_info = """
    CREATE TABLE clients.client_latest (
        client_hub_key UUID PRIMARY KEY,
        client_name VARCHAR(255),
        fiscal_year_end DATE
    );
    
    CREATE TABLE participants.participant_detail (
        participant_hub_key UUID PRIMARY KEY,
        employee_type VARCHAR(50),
        status VARCHAR(20),
        termination_date DATE
    );
    """
    
    # Test queries
    test_queries = [
        "Show all active officers",
        "Find officers with 10b5-1 plans in Q4 by US region",
        "Show participants with vesting in next month",
        "List active participants by region with grant counts"
    ]
    
    for query in test_queries:
        print(f"\n{'='*50}")
        print(f"Processing: {query}")
        print(f"{'='*50}")
        
        result = await processor.process_query(
            user_query=query,
            table_info=table_info
        )
        
        if result['success']:
            print(f"Query Type: {result['query_type']}")
            print(f"Entity Discovery Used: {result['entity_discovery_used']}")
            print(f"Date Processing Used: {result['date_processing_used']}")
            print(f"\nGenerated SQL:\n{result['sql']}")
        else:
            print(f"Error: {result['error']}")


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Run the example
    asyncio.run(main())
