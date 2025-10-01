import React, { useState } from 'react';
import { FileCode, Server, Database, Settings, Cpu, Lock, MessageSquare } from 'lucide-react';

const CompletePipelineWalkthrough = () => {
  const [expandedStep, setExpandedStep] = useState(1);

  const steps = [
    {
      id: 1,
      name: 'Query Understanding',
      type: 'LLM',
      duration: '320ms',
      cost: '$0.002',
      files: [
        {
          path: 'pipeline/steps/understanding.py',
          class: 'QueryUnderstandingStep',
          methods: ['execute()', 'calculate_ambiguity_score()']
        }
      ],
      services: [
        {
          name: 'LLM Service',
          path: 'services/llm_service.py',
          purpose: 'Call GPT-4/Claude API'
        }
      ],
      config: [
        {
          file: 'config/prompts/understanding.yaml',
          contains: 'Understanding prompt template'
        }
      ],
      input: {
        from: 'User / API Request',
        data: 'Raw user query string'
      },
      processing: [
        '1. Load understanding prompt from config/prompts/understanding.yaml',
        '2. Format prompt with user query',
        '3. Call LLM Service (llm_service.call())',
        '4. Parse LLM response JSON',
        '5. Calculate ambiguity score',
        '6. If ambiguity > 70: raise NeedsClarificationException',
        '7. Return QueryContext with corrected query'
      ],
      output: {
        to: 'Step 2',
        data: 'QueryContext(corrected_query, intent, complexity)'
      },
      code_snippet: `# pipeline/steps/understanding.py
class QueryUnderstandingStep:
    def __init__(self, llm_service, config):
        self.llm = llm_service
        self.prompt_template = config.load('prompts/understanding.yaml')
    
    async def execute(self, context: QueryContext) -> QueryContext:
        # Format prompt
        prompt = self.prompt_template.format(
            query=context.original_query
        )
        
        # Call LLM
        result = await self.llm.call(
            prompt=prompt,
            model="gpt-4-turbo",
            max_tokens=300
        )
        
        # Calculate ambiguity
        ambiguity_score = self.calculate_ambiguity_score(result)
        
        if ambiguity_score > 70:
            raise NeedsClarificationException(result)
        
        # Update context
        context.corrected_query = result['corrected_query']
        context.intent = result['intent']
        context.complexity = result['complexity']
        
        return context`
    },
    {
      id: 2,
      name: 'Query Type Classification',
      type: 'LLM',
      duration: '180ms',
      cost: '$0.001',
      files: [
        {
          path: 'pipeline/steps/classification.py',
          class: 'QueryTypeClassificationStep',
          methods: ['execute()']
        }
      ],
      services: [
        {
          name: 'LLM Service',
          path: 'services/llm_service.py',
          purpose: 'Call GPT-3.5 for classification'
        }
      ],
      config: [
        {
          file: 'config/prompts/classification.yaml',
          contains: 'Classification prompt with query types'
        },
        {
          file: 'config/query_types.yaml',
          contains: 'List of all query type definitions'
        }
      ],
      input: {
        from: 'Step 1',
        data: 'QueryContext with corrected_query'
      },
      processing: [
        '1. Load classification prompt',
        '2. Load query type definitions from config',
        '3. Format prompt with query types list',
        '4. Call LLM (cheaper model for classification)',
        '5. Validate returned query_type exists',
        '6. Add to context'
      ],
      output: {
        to: 'Step 3',
        data: 'QueryContext + query_type'
      },
      code_snippet: `# pipeline/steps/classification.py
class QueryTypeClassificationStep:
    def __init__(self, llm_service, config):
        self.llm = llm_service
        self.query_types = config.load('query_types.yaml')
        self.prompt = config.load('prompts/classification.yaml')
    
    async def execute(self, context: QueryContext) -> QueryContext:
        prompt = self.prompt.format(
            query=context.corrected_query,
            query_types=self.query_types.list()
        )
        
        result = await self.llm.call(
            prompt=prompt,
            model="gpt-3.5-turbo",
            max_tokens=100
        )
        
        # Validate query type
        if result['query_type'] not in self.query_types:
            result['query_type'] = 'UNKNOWN'
        
        context.query_type = result['query_type']
        context.classification_confidence = result['confidence']
        
        return context`
    },
    {
      id: 3,
      name: 'Entity Extraction',
      type: 'LLM',
      duration: '450ms',
      cost: '$0.003',
      files: [
        {
          path: 'pipeline/steps/entity_extraction.py',
          class: 'EntityExtractionStep',
          methods: ['execute()']
        }
      ],
      services: [
        {
          name: 'LLM Service',
          path: 'services/llm_service.py',
          purpose: 'Extract entities from query'
        },
        {
          name: 'Domain Knowledge Service',
          path: 'services/domain_knowledge_service.py',
          purpose: 'Match user phrases to domain concepts'
        }
      ],
      config: [
        {
          file: 'config/prompts/entity_extraction.yaml',
          contains: 'Entity extraction prompt'
        },
        {
          file: 'config/domain_definitions.yaml',
          contains: 'Known entity types and patterns'
        }
      ],
      input: {
        from: 'Step 2',
        data: 'QueryContext with query_type'
      },
      processing: [
        '1. Load entity extraction prompt',
        '2. Load entity types from domain_definitions.yaml',
        '3. Format prompt with entity types',
        '4. Call LLM for extraction',
        '5. Use DomainKnowledgeService to match phrases',
        '   - "last release" → release concept',
        '   - "had issues" → issue types',
        '6. Add raw entities to context'
      ],
      output: {
        to: 'Step 4',
        data: 'QueryContext + raw_entities'
      },
      code_snippet: `# pipeline/steps/entity_extraction.py
class EntityExtractionStep:
    def __init__(self, llm_service, domain_service, config):
        self.llm = llm_service
        self.domain = domain_service
        self.prompt = config.load('prompts/entity_extraction.yaml')
        self.entity_types = config.load('domain_definitions.yaml')
    
    async def execute(self, context: QueryContext) -> QueryContext:
        prompt = self.prompt.format(
            query=context.corrected_query,
            entity_types=self.entity_types['entity_types']
        )
        
        result = await self.llm.call(
            prompt=prompt,
            model="gpt-4-turbo",
            max_tokens=500
        )
        
        # Enrich with domain knowledge
        if 'date_expressions' in result:
            result['release_concept'] = await self.domain.match_release_phrase(
                result['date_expressions']
            )
        
        if 'issue_phrases' in result:
            result['issue_types'] = self.domain.match_issue_phrases(
                result['issue_phrases']
            )
        
        context.raw_entities = result
        return context`
    },
    {
      id: 4,
      name: 'Entity Normalization',
      type: 'Deterministic + DB',
      duration: '180ms',
      cost: '$0',
      files: [
        {
          path: 'pipeline/steps/normalization.py',
          class: 'EntityNormalizationStep',
          methods: ['execute()', 'normalize_clients()', 'normalize_dates()', 'normalize_statuses()']
        }
      ],
      services: [
        {
          name: 'Domain Knowledge Service',
          path: 'services/domain_knowledge_service.py',
          purpose: 'Resolve release concepts, calculate dates'
        },
        {
          name: 'Database Service',
          path: 'services/database_service.py',
          purpose: 'Lookup client IDs, participant IDs'
        }
      ],
      config: [
        {
          file: 'config/domain_definitions.yaml',
          contains: 'Release type definitions'
        },
        {
          file: 'config/table_mappings.yaml',
          contains: 'Table/column mappings'
        }
      ],
      input: {
        from: 'Step 3',
        data: 'QueryContext + raw_entities'
      },
      processing: [
        '1. For each entity type, normalize to DB values:',
        '',
        '2. Client names → client_ids:',
        '   - Query database: SELECT id FROM clients WHERE name ILIKE...',
        '',
        '3. "Last release" → actual date:',
        '   - Call domain_service.resolve_release_concept()',
        '   - Uses ReleaseCalculator to query MAX(vest_date)',
        '',
        '4. "Had issues" → issue types:',
        '   - Call domain_service.resolve_issue_types()',
        '   - Returns IssueDefinition objects',
        '',
        '5. Date expressions → ISO dates:',
        '   - "next 30 days" → start/end dates',
        '',
        '6. Status terms → enum values:',
        '   - "active" → \'active\'',
        '   - "unvested" → \'pending\'',
        '',
        '7. Apply user security context',
        '   - Filter to accessible_clients'
      ],
      output: {
        to: 'Step 5',
        data: 'QueryContext + normalized_entities'
      },
      code_snippet: `# pipeline/steps/normalization.py
class EntityNormalizationStep:
    def __init__(self, domain_service, db_service, config):
        self.domain = domain_service
        self.db = db_service
        self.mappings = config.load('table_mappings.yaml')
    
    async def execute(
        self, 
        context: QueryContext, 
        user_context: UserContext
    ) -> QueryContext:
        normalized = {}
        
        # Normalize client names
        if context.raw_entities.get('client_names'):
            normalized['client_ids'] = await self.db.lookup_clients(
                context.raw_entities['client_names']
            )
        
        # Resolve "last release"
        if context.raw_entities.get('release_concept'):
            release_info = await self.domain.resolve_release_concept(
                phrase=context.raw_entities['release_concept'],
                client_ids=user_context.accessible_clients
            )
            normalized.update(release_info)
        
        # Resolve issue types
        if context.raw_entities.get('issue_types'):
            issue_defs = await self.domain.resolve_issue_types(
                context.raw_entities['issue_types']
            )
            normalized['issue_definitions'] = issue_defs
        
        # Normalize dates
        if context.raw_entities.get('date_expressions'):
            normalized['date_range'] = self.normalize_dates(
                context.raw_entities['date_expressions']
            )
        
        # Apply security
        normalized['accessible_clients'] = user_context.accessible_clients
        
        context.normalized_entities = normalized
        return context`
    },
    {
      id: 5,
      name: 'Template Parameter Extraction',
      type: 'LLM',
      duration: '420ms',
      cost: '$0.003',
      files: [
        {
          path: 'pipeline/steps/parameter_extraction.py',
          class: 'TemplateParameterExtractionStep',
          methods: ['execute()', 'get_prompt_for_query_type()']
        }
      ],
      services: [
        {
          name: 'LLM Service',
          path: 'services/llm_service.py',
          purpose: 'Extract template-specific parameters'
        }
      ],
      config: [
        {
          file: 'config/prompts/parameters/{query_type}.yaml',
          contains: 'Template-specific parameter prompts'
        },
        {
          file: 'config/query_types.yaml',
          contains: 'Required parameters per query type'
        }
      ],
      input: {
        from: 'Step 4',
        data: 'QueryContext + normalized_entities'
      },
      processing: [
        '1. Load query type definition',
        '2. Get template-specific prompt:',
        '   - config/prompts/parameters/vesting_schedule.yaml',
        '3. Format prompt with normalized entities',
        '4. Call LLM to extract parameters:',
        '   - Which metrics to show?',
        '   - Which computed fields?',
        '   - How to order results?',
        '   - Pagination settings?',
        '5. Validate required parameters present',
        '6. Add defaults for optional parameters'
      ],
      output: {
        to: 'Step 6',
        data: 'QueryContext + template_params'
      },
      code_snippet: `# pipeline/steps/parameter_extraction.py
class TemplateParameterExtractionStep:
    def __init__(self, llm_service, config):
        self.llm = llm_service
        self.config = config
    
    async def execute(self, context: QueryContext) -> QueryContext:
        # Load query-type-specific prompt
        prompt_file = f'prompts/parameters/{context.query_type}.yaml'
        prompt_template = self.config.load(prompt_file)
        
        # Format with normalized entities
        prompt = prompt_template.format(
            query=context.corrected_query,
            entities=context.normalized_entities
        )
        
        # Extract parameters
        result = await self.llm.call(
            prompt=prompt,
            model="gpt-4-turbo",
            max_tokens=500
        )
        
        # Validate required params
        required = self.config.get_required_params(context.query_type)
        for param in required:
            if param not in result:
                raise MissingParameterException(param)
        
        # Add defaults
        defaults = self.config.get_default_params(context.query_type)
        result = {**defaults, **result}
        
        context.template_params = result
        return context`
    },
    {
      id: 6,
      name: 'Template Population',
      type: 'Deterministic',
      duration: '60ms',
      cost: '$0',
      files: [
        {
          path: 'pipeline/steps/template_population.py',
          class: 'TemplatePopulationStep',
          methods: ['execute()', 'build_metrics()', 'build_joins()', 'build_filters()']
        }
      ],
      services: [
        {
          name: 'Domain Knowledge Service',
          path: 'services/domain_knowledge_service.py',
          purpose: 'Build issue detection queries'
        },
        {
          name: 'Template Engine',
          path: 'services/template_engine.py',
          purpose: 'Load and populate SQL templates'
        }
      ],
      config: [
        {
          file: 'config/sql_templates/{query_type}.sql',
          contains: 'SQL skeleton templates'
        },
        {
          file: 'config/table_mappings.yaml',
          contains: 'Metric definitions, join rules'
        }
      ],
      input: {
        from: 'Step 5',
        data: 'QueryContext + template_params + normalized_entities'
      },
      processing: [
        '1. Load SQL template for query type:',
        '   - config/sql_templates/vesting_schedule.sql',
        '',
        '2. Build metrics clause:',
        '   - Map metric names to SQL expressions',
        '   - Use table_mappings.yaml definitions',
        '',
        '3. Build joins clause:',
        '   - Determine needed joins based on metrics',
        '   - Use table_mappings.yaml join rules',
        '',
        '4. Build filters clause:',
        '   - Convert normalized entities to WHERE clauses',
        '   - For issues: call domain_service.build_issue_detection_query()',
        '',
        '5. Populate template:',
        '   - String replacement (no LLM!)',
        '   - Inject metrics, joins, filters',
        '',
        '6. Format and validate SQL syntax'
      ],
      output: {
        to: 'Step 7',
        data: 'QueryContext + sql'
      },
      code_snippet: `# pipeline/steps/template_population.py
class TemplatePopulationStep:
    def __init__(self, template_engine, domain_service, config):
        self.templates = template_engine
        self.domain = domain_service
        self.mappings = config.load('table_mappings.yaml')
    
    def execute(
        self, 
        context: QueryContext, 
        user_context: UserContext
    ) -> QueryContext:
        # Load template
        template = self.templates.load(context.query_type)
        
        # Build components
        metrics = self.build_metrics(
            context.template_params['metrics']
        )
        
        joins = self.build_joins(
            context.template_params['metrics'],
            context.query_type
        )
        
        filters = self.build_filters(
            context.normalized_entities,
            context.template_params
        )
        
        # Special handling for issue detection
        if 'issue_definitions' in context.normalized_entities:
            filters += self.domain.build_issue_detection_query(
                context.normalized_entities['issue_definitions'],
                context.normalized_entities['date_filter']
            )
        
        # Populate template
        sql = template.format(
            metrics=metrics,
            joins=joins,
            filters=filters,
            accessible_clients=user_context.accessible_clients,
            ordering=context.template_params['ordering'],
            limit=context.template_params['limit']
        )
        
        context.sql = sql
        return context
    
    def build_metrics(self, metric_names):
        return ',\\n    '.join([
            self.mappings['metrics'][m] 
            for m in metric_names
        ])`
    },
    {
      id: 7,
      name: 'Security Validation',
      type: 'Deterministic',
      duration: '95ms',
      cost: '$0',
      files: [
        {
          path: 'pipeline/steps/security_validation.py',
          class: 'SecurityValidationStep',
          methods: ['execute()', 'validate_client_access()', 'inject_rls()']
        }
      ],
      services: [
        {
          name: 'Security Service',
          path: 'services/security_service.py',
          purpose: 'Verify permissions, log audit'
        },
        {
          name: 'Database Service',
          path: 'services/database_service.py',
          purpose: 'Validate SQL, check RLS policies'
        }
      ],
      config: [
        {
          file: 'config/security/rls_policies.yaml',
          contains: 'Row-level security rules'
        }
      ],
      input: {
        from: 'Step 6',
        data: 'QueryContext + sql'
      },
      processing: [
        '1. Parse SQL to extract tables and filters',
        '',
        '2. Verify client access:',
        '   - Check WHERE clause has client_id filter',
        '   - Verify client_ids match user accessible_clients',
        '',
        '3. Check RLS policies:',
        '   - Load policies from config',
        '   - Ensure SQL complies with policies',
        '',
        '4. Validate no SQL injection:',
        '   - Check for suspicious patterns',
        '   - Validate all parameters sanitized',
        '',
        '5. Log audit trail:',
        '   - security_service.log_query_attempt()',
        '   - Record user, query, timestamp',
        '',
        '6. If validation fails: raise SecurityException'
      ],
      output: {
        to: 'Step 8',
        data: 'QueryContext + validated sql'
      },
      code_snippet: `# pipeline/steps/security_validation.py
class SecurityValidationStep:
    def __init__(self, security_service, config):
        self.security = security_service
        self.rls_policies = config.load('security/rls_policies.yaml')
    
    def execute(
        self, 
        context: QueryContext, 
        user_context: UserContext
    ) -> QueryContext:
        # Parse SQL
        tables = self.parse_tabl
