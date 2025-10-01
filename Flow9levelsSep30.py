from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class QueryContext:
    """Carries state through the entire pipeline"""
    original_query: str
    corrected_query: str = None
    intent: str = None
    complexity: str = None
    query_type: str = None
    raw_entities: Dict = None
    normalized_entities: Dict = None
    template_params: Dict = None
    sql: str = None
    results: List = None
    response: str = None

class CompletePipeline:
    """Orchestrates all 9 steps"""
    
    def __init__(self):
        self.understanding = QueryUnderstandingStep()
        self.classifier = QueryTypeClassificationStep()
        self.entity_extractor = EntityExtractionStep()
        self.normalizer = EntityNormalizationStep()
        self.param_extractor = TemplateParameterExtractionStep()
        self.template_engine = TemplatePopulationStep()
        self.security = SecurityValidationStep()
        self.db = DatabaseExecutionStep()
        self.formatter = ResponseFormattingStep()
    
    async def process(self, user_query: str, user_context: Dict) -> Dict:
        """Execute all 9 steps in sequence"""
        
        context = QueryContext(original_query=user_query)
        
        # STEP 1: Query Understanding
        context = await self.understanding.execute(context)
        
        # STEP 2: Query Type Classification
        context = await self.classifier.execute(context)
        
        # STEP 3: Entity Extraction
        context = await self.entity_extractor.execute(context)
        
        # STEP 4: Entity Normalization (uses database)
        context = await self.normalizer.execute(context, user_context)
        
        # STEP 5: Template Parameter Extraction
        context = await self.param_extractor.execute(context)
        
        # STEP 6: Template Population (deterministic)
        context = self.template_engine.execute(context, user_context)
        
        # STEP 7: Security Validation
        context = self.security.execute(context, user_context)
        
        # STEP 8: Database Execution
        context = await self.db.execute(context)
        
        # STEP 9: Response Formatting
        context = await self.formatter.execute(context)
        
        return {
            "sql": context.sql,
            "results": context.results,
            "response": context.response,
            "metadata": {
                "query_type": context.query_type,
                "entities": context.normalized_entities,
                "intent": context.intent
            }
        }

class QueryUnderstandingStep:
    """STEP 1: Parse intent, correct typos, assess complexity"""
    
    PROMPT = """
    Parse and understand this equity plan query.
    
    Query: "{query}"
    
    Tasks:
    1. Correct any typos or grammatical errors
    2. Identify the user's intent (list/aggregate/compare/calculate/search)
    3. Assess complexity (simple/medium/complex)
    4. Determine if clarification is needed
    
    Output JSON:
    {{
      "corrected_query": "corrected version",
      "intent": "aggregate",
      "complexity": "medium",
      "requires_clarification": false,
      "clarification_question": null
    }}
    """
    
    async def execute(self, context: QueryContext) -> QueryContext:
        result = await llm.call(
            prompt=self.PROMPT.format(query=context.original_query),
            model="gpt-4-turbo",
            max_tokens=300
        )
        
        context.corrected_query = result['corrected_query']
        context.intent = result['intent']
        context.complexity = result['complexity']
        
        if result['requires_clarification']:
            raise NeedsClarificationException(result['clarification_question'])
        
        return context

class QueryTypeClassificationStep:
    """STEP 2: Identify which template category"""
    
    PROMPT = """
    Classify this query into a template category.
    
    Query: "{query}"
    
    Categories:
    - CLIENT_LEVEL: Company-wide aggregations
    - PARTICIPANT_LEVEL: Individual employee details
    - VESTING_SCHEDULE: Time-based vesting analysis
    - REGIONAL: Geographic breakdowns
    - FINANCIAL_METRICS: Burn rate, expense, dilution
    - COMPLIANCE_AUDIT: Regulatory compliance
    - UNKNOWN: Doesn't fit templates
    
    Output JSON:
    {{
      "query_type": "CLIENT_LEVEL",
      "confidence": 0.95
    }}
    """
    
    async def execute(self, context: QueryContext) -> QueryContext:
        result = await llm.call(
            prompt=self.PROMPT.format(query=context.corrected_query),
            model="gpt-3.5-turbo",  # Cheaper for classification
            max_tokens=100
        )
        
        context.query_type = result['query_type']
        return context

class EntityExtractionStep:
    """STEP 3: Identify entities in the query"""
    
    PROMPT = """
    Extract entities from this equity plan query.
    
    Query: "{query}"
    
    Entity types to extract:
    - client_names: Company names (e.g., "ABC Corp")
    - participant_names: Employee names (e.g., "John Smith")
    - plan_types: Equity plan types (RSU, ISO, NSO, ESPP, etc.)
    - statuses: Status filters (active, terminated, vested, unvested)
    - date_expressions: Time references (e.g., "next 30 days", "Q4 2025")
    - metrics: What to measure (count, sum, average, etc.)
    - departments: Department names
    - countries: Geographic locations
    
    Output JSON with ALL entities found:
    {{
      "client_names": ["ABC Corp"],
      "participant_names": [],
      "plan_types": [],
      "statuses": ["active"],
      "date_expressions": [],
      "metrics": ["participant_count", "plan_count"],
      "departments": [],
      "countries": []
    }}
    """
    
    async def execute(self, context: QueryContext) -> QueryContext:
        result = await llm.call(
            prompt=self.PROMPT.format(query=context.corrected_query),
            model="gpt-4-turbo",
            max_tokens=500
        )
        
        context.raw_entities = result
        return context

class EntityNormalizationStep:
    """STEP 4: Convert raw entities to database values"""
    
    def __init__(self):
        self.db = Database()
    
    async def execute(
        self, 
        context: QueryContext, 
        user_context: Dict
    ) -> QueryContext:
        normalized = {}
        
        # Normalize client names to IDs
        if context.raw_entities.get('client_names'):
            normalized['client_ids'] = await self._normalize_clients(
                context.raw_entities['client_names']
            )
        
        # Normalize participant names to IDs
        if context.raw_entities.get('participant_names'):
            normalized['participant_ids'] = await self._normalize_participants(
                context.raw_entities['participant_names'],
                user_context['accessible_clients']
            )
        
        # Normalize date expressions to actual dates
        if context.raw_entities.get('date_expressions'):
            normalized['date_range'] = self._normalize_dates(
                context.raw_entities['date_expressions']
            )
        
        # Normalize statuses to enum values
        if context.raw_entities.get('statuses'):
            normalized['status_filters'] = self._normalize_statuses(
                context.raw_entities['statuses']
            )
        
        # Pass through plan types (already normalized)
        if context.raw_entities.get('plan_types'):
            normalized['plan_types'] = context.raw_entities['plan_types']
        
        # Add user's accessible clients
        normalized['accessible_clients'] = user_context['accessible_clients']
        
        context.normalized_entities = normalized
        return context
    
    async def _normalize_clients(self, client_names: List[str]) -> List[int]:
        """Convert company names to client IDs"""
        results = await self.db.execute("""
            SELECT id FROM clients 
            WHERE name ILIKE ANY($1)
        """, [f"%{name}%" for name in client_names])
        
        return [r['id'] for r in results]
    
    async def _normalize_participants(
        self, 
        names: List[str], 
        accessible_clients: List[int]
    ) -> List[int]:
        """Convert participant names to IDs (with security filter)"""
        results = await self.db.execute("""
            SELECT id FROM participants 
            WHERE name ILIKE ANY($1)
              AND client_id = ANY($2)
        """, [f"%{name}%" for name in names], accessible_clients)
        
        return [r['id'] for r in results]
    
    def _normalize_dates(self, date_expressions: List[str]) -> Dict:
        """Convert natural language dates to ISO format"""
        today = datetime.now().date()
        
        for expr in date_expressions:
            expr_lower = expr.lower()
            
            if 'next 30 days' in expr_lower:
                return {
                    'start': today.isoformat(),
                    'end': (today + timedelta(days=30)).isoformat()
                }
            elif 'next 60 days' in expr_lower:
                return {
                    'start': today.isoformat(),
                    'end': (today + timedelta(days=60)).isoformat()
                }
            elif 'next 90 days' in expr_lower:
                return {
                    'start': today.isoformat(),
                    'end': (today + timedelta(days=90)).isoformat()
                }
            elif 'q4 2025' in expr_lower:
                return {
                    'start': '2025-10-01',
                    'end': '2025-12-31'
                }
            elif 'this year' in expr_lower:
                year = today.year
                return {
                    'start': f'{year}-01-01',
                    'end': f'{year}-12-31'
                }
        
        return None
    
    def _normalize_statuses(self, statuses: List[str]) -> List[str]:
        """Normalize status terms to database enum values"""
        STATUS_MAP = {
            'active': 'active',
            'terminated': 'terminated',
            'on leave': 'on_leave',
            'vested': 'vested',
            'unvested': 'pending',
            'forfeited': 'forfeited',
            'exercised': 'exercised',
            'expired': 'expired'
        }
        
        return [STATUS_MAP.get(s.lower(), s) for s in statuses]

class TemplateParameterExtractionStep:
    """STEP 5: Extract template-specific parameters"""
    
    TEMPLATES = {
        'CLIENT_LEVEL': """
        Extract parameters for CLIENT_LEVEL template.
        
        Query: "{query}"
        Normalized entities: {entities}
        
        Parameters to extract:
        - metrics: Which aggregations? (participant_count, plan_count, etc.)
        - ordering: Sort order (e.g., "participant_count DESC")
        - limit: How many results?
        - include_zeros: Include companies with 0 participants/plans?
        
        Output JSON
        """,
        
        'PARTICIPANT_LEVEL': """
        Extract parameters for PARTICIPANT_LEVEL template.
        
        Query: "{query}"
        Normalized entities: {entities}
        
        Parameters to extract:
        - metrics: What to show? (grant_count, vested_shares, unvested_shares)
        - grant_status_filter: vested/unvested/all
        - ordering: Sort by what?
        - limit: How many participants?
        
        Output JSON
        """,
        
        'VESTING_SCHEDULE': """
        Extract parameters for VESTING_SCHEDULE template.
        
        Query: "{query}"
        Normalized entities: {entities}
        
        Parameters to extract:
        - computed_fields: Calculate vest value? Days until vest?
        - vesting_status: pending/vested/all
        - urgency_grouping: Group by urgency level?
        - ordering: By date or participant?
        
        Output JSON
        """
    }
    
    async def execute(self, context: QueryContext) -> QueryContext:
        prompt_template = self.TEMPLATES.get(context.query_type)
        
        if not prompt_template:
            raise TemplateNotFoundException(context.query_type)
        
        result = await llm.call(
            prompt=prompt_template.format(
                query=context.corrected_query,
                entities=json.dumps(context.normalized_entities)
            ),
            model="gpt-4-turbo",
            max_tokens=500
        )
        
        context.template_params = result
        return context

class TemplatePopulationStep:
    """STEP 6: Fill template with parameters (deterministic)"""
    
    TEMPLATES = {
        'CLIENT_LEVEL': """
            SELECT 
                c.id,
                c.name,
                {metrics}
            FROM clients c
            {joins}
            WHERE c.id IN ({accessible_clients})
                {filters}
            GROUP BY c.id, c.name
            {ordering}
            LIMIT {limit}
        """
    }
    
    def execute(
        self, 
        context: QueryContext, 
        user_context: Dict
    ) -> QueryContext:
        template = self.TEMPLATES[context.query_type]
        params = context.template_params
        entities = context.normalized_entities
        
        # Build metrics clause
        metrics = self._build_metrics(params['metrics'])
        
        # Build joins
        joins = self._build_joins(params['metrics'])
        
        # Build filters
        filters = self._build_filters(entities)
        
        # Populate template
        sql = template.format(
            metrics=metrics,
            joins=joins,
            accessible_clients=','.join(map(str, entities['accessible_clients'])),
            filters=filters,
            ordering=params.get('ordering', ''),
            limit=params.get('limit', 100)
        )
        
        context.sql = sql
        return context
    
    def _build_metrics(self, metric_names: List[str]) -> str:
        # Same as before...
        pass
    
    def _build_joins(self, metric_names: List[str]) -> str:
        # Same as before...
        pass
    
    def _build_filters(self, entities: Dict) -> str:
        # Same as before...
        pass

class SecurityValidationStep:
    """STEP 7: Verify RLS and inject security clauses"""
    
    def execute(
        self, 
        context: QueryContext, 
        user_context: Dict
    ) -> QueryContext:
        # Verify all client IDs in query are accessible
        # Log audit trail
        # Inject additional security WHERE clauses if needed
        
        # Validation logic here...
        
        return context

class DatabaseExecutionStep:
    """STEP 8: Execute on PostgreSQL"""
    
    async def execute(self, context: QueryContext) -> QueryContext:
        results = await self.db.execute(context.sql, timeout=30)
        context.results = results
        return context

class ResponseFormattingStep:
    """STEP 9: Generate natural language response"""
    
    PROMPT = """
    Format these query results into a helpful response.
    
    User's original question: "{original_query}"
    Query results: {results}
    
    Create a natural language response that:
    1. Summarizes the key findings
    2. Presents data in a table if multiple rows
    3. Adds 1-2 insights
    4. Suggests relevant follow-up questions
    
    Keep under 500 words.
    """
    
    async def execute(self, context: QueryContext) -> QueryContext:
        result = await llm.call(
            prompt=self.PROMPT.format(
                original_query=context.original_query,
                results=json.dumps(context.results[:10])  # First 10 rows
            ),
            model="gpt-4-turbo",
            max_tokens=800
        )
        
        context.response = result
        return context
