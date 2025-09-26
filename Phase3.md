📋 Phase 3 Overview
Phase 3: Intelligence adds adaptive reasoning to handle real-world query complexity:

EntityDiscovery → Handles data variations ("US" finds all database variants)
DateProcessor → Resolves complex temporal logic (fiscal quarters, business events)

This phase transforms ambiguous user input into precise database logic.
🔍 Component 1: EntityDiscovery
Purpose:
Automatically discovers and maps data variations. When user says "US", it finds all database variations like "USA", "United States", "U.S." and provides mapping context to GPT-4o.
Step 1: Entity Type Classification
pythonclass EntityType(Enum):
    """Types of entities that need discovery"""
    GEOGRAPHIC = "geographic"      # Countries, regions, states
    ORGANIZATIONAL = "organizational"  # Departments, divisions, roles
    STATUS = "status"             # Employment status, grant status  
    EQUITY_SPECIFIC = "equity_specific"  # Plan types, security types
    TEMPORAL = "temporal"         # Date references, periods
Step 2: Entity Extraction Engine
pythonclass EntityDiscovery:
    def __init__(self, db_connection: Optional[Any] = None, openai_client: Optional[Any] = None):
        self.db = db_connection
        self.openai_client = openai_client
        self.discovery_cache = {}  # Performance optimization
        self.extraction_patterns = self._load_extraction_patterns()
        self.common_mappings = self._load_common_mappings()
    
    def _load_extraction_patterns(self) -> Dict:
        """Patterns to identify discoverable entities in queries"""
        return {
            'geographic': [
                r'\b(US|USA|UK|Germany|France|Canada)\b',           # Country codes/names
                r'\b(region|country|state|territory)\b',            # Geographic terms
                r'\b(EMEA|APAC|Americas|Europe|Asia)\b'             # Business regions
            ],
            'organizational': [
                r'\b(IT|HR|engineering|sales|marketing|finance)\b', # Departments  
                r'\b(officers?|executives?|managers?|employees?)\b', # Job roles
                r'\b(department|division|team|group)\b'             # Org terms
            ],
            'status': [
                r'\b(active|terminated|employed|current)\b',        # Employment status
                r'\b(vested|unvested|exercised|forfeited)\b',       # Grant status
                r'\b(pending|approved|cancelled)\b'                # General status
            ],
            'equity_specific': [
                r'\b(ISO|NQSO|RSU|RSA|options?|grants?)\b',        # Security types
                r'\b(10b5-1|trading.?plan|blackout)\b',            # Compliance terms
                r'\b(cliff|vest|exercise|accelerat)\w*\b'           # Vesting terms
            ]
        }
    
    def _load_common_mappings(self) -> Dict:
        """Pre-defined mappings for common variations"""
        return {
            'geographic': {
                'US': ['US', 'USA', 'United States', 'U.S.', 'U.S.A.', 'America'],
                'UK': ['UK', 'United Kingdom', 'Britain', 'Great Britain', 'GBR'],
                'Germany': ['Germany', 'Deutschland', 'DE', 'DEU']
            },
            'organizational': {
                'IT': ['IT', 'Information Technology', 'InfoTech', 'Tech', 'Technology'],
                'HR': ['HR', 'Human Resources', 'People Operations', 'Talent', 'Personnel']
            },
            'status': {
                'active': ['active', 'employed', 'current', 'working', 'present'],
                'terminated': ['terminated', 'former', 'ex-employee', 'departed', 'left']
            },
            'equity_specific': {
                'stock_options': ['ISO', 'NQSO', 'stock options', 'options', 'stock option'],
                'restricted_stock': ['RSU', 'RSA', 'restricted stock', 'restricted units']
            }
        }
Step 3: Multi-Strategy Entity Extraction
pythonasync def discover_entities(self, user_query: str) -> str:
    """Main discovery pipeline with multiple extraction strategies"""
    
    # Step 1: Extract potential entities using patterns
    candidate_entities = self._extract_candidate_entities(user_query)
    
    if not candidate_entities:
        return ""  # No entities need discovery
    
    # Step 2: Validate and enrich entities  
    validated_entities = await self._validate_entities(candidate_entities, user_query)
    
    # Step 3: Discover variations for each entity
    discovery_results = {}
    for entity in validated_entities:
        discovery_results[entity['value']] = await self._discover_entity_variations(entity)
    
    # Step 4: Build discovery context for GPT-4o
    return self._build_discovery_context(discovery_results)

def _extract_candidate_entities(self, query: str) -> List[Dict]:
    """Extract entities using pattern matching"""
    
    entities = []
    
    for entity_type, patterns in self.extraction_patterns.items():
        for pattern in patterns:
            matches = re.finditer(pattern, query, re.IGNORECASE)
            for match in matches:
                entity_value = match.group(0)
                
                # Determine likely database table/column
                table_mapping = self._get_table_mapping(entity_type, entity_value)
                
                entities.append({
                    'type': entity_type,
                    'value': entity_value.upper() if entity_type == 'geographic' else entity_value.lower(),
                    'table': table_mapping['table'],
                    'column': table_mapping['column'],
                    'confidence': 0.8,  # Pattern-based confidence
                    'context_words': self._get_context_words(query, match.start(), match.end())
                })
    
    return entities

def _get_table_mapping(self, entity_type: str, entity_value: str) -> Dict:
    """Map entity types to likely database locations"""
    
    mappings = {
        'geographic': {
            'table': 'participants.participant_address',
            'column': 'country_code'  # or region_code based on context
        },
        'organizational': {
            'table': 'participants.participant_employer_detail', 
            'column': 'department'
        },
        'status': {
            'table': 'participants.participant_detail',
            'column': 'status'
        },
        'equity_specific': {
            'table': 'grants.grant_latest',
            'column': 'grant_type'
        }
    }
    
    return mappings.get(entity_type, {'table': 'unknown', 'column': 'unknown'})

def _get_context_words(self, query: str, start: int, end: int) -> List[str]:
    """Get surrounding words for context"""
    words = query.split()
    query_words = ' '.join(words)
    
    # Find the entity in the word list and get surrounding context
    entity_word_idx = None
    for i, word in enumerate(words):
        if query_words.find(word, start) != -1:
            entity_word_idx = i
            break
    
    if entity_word_idx is not None:
        # Get 2 words before and after for context
        context_start = max(0, entity_word_idx - 2)
        context_end = min(len(words), entity_word_idx + 3)
        return words[context_start:context_end]
    
    return []
Step 4: LLM-Enhanced Entity Validation
pythonasync def _validate_entities(self, candidates: List[Dict], query: str) -> List[Dict]:
    """Use GPT-4o to validate and enrich entity extraction"""
    
    if not self.openai_client:
        return candidates  # Skip LLM validation if not available
    
    validation_prompt = f"""
    Analyze this equity management query and validate the extracted entities:
    
    Query: "{query}"
    
    Extracted Entities:
    {json.dumps([{'type': e['type'], 'value': e['value'], 'context': e['context_words']} for e in candidates], indent=2)}
    
    For each entity, determine:
    1. Is it actually an entity that might have data variations?
    2. What type of entity is it really?
    3. What confidence level (0.0-1.0)?
    4. Any additional context or corrections?
    
    Return JSON format:
    {{
        "validated_entities": [
            {{
                "value": "US",
                "type": "geographic", 
                "confidence": 0.9,
                "corrections": "Should look for country variations",
                "likely_table": "participant_address",
                "likely_column": "country_code"
            }}
        ]
    }}
    """
    
    try:
        response = await self.openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": validation_prompt}],
            temperature=0.1,
            max_tokens=1000
        )
        
        result = json.loads(response.choices[0].message.content)
        
        # Merge LLM insights with original candidates
        validated = []
        for entity_data in result.get('validated_entities', []):
            if entity_data['confidence'] > 0.5:  # Only keep high-confidence entities
                # Find original candidate to merge data
                original = next((c for c in candidates if c['value'] == entity_data['value']), None)
                if original:
                    original.update({
                        'confidence': entity_data['confidence'],
                        'llm_corrections': entity_data.get('corrections', ''),
                        'validated': True
                    })
                    validated.append(original)
        
        return validated
        
    except Exception as e:
        logging.error(f"LLM entity validation failed: {e}")
        return candidates  # Fall back to original candidates
Step 5: Database Discovery Engine
pythonasync def _discover_entity_variations(self, entity: Dict) -> Dict:
    """Multi-strategy approach to find database variations"""
    
    # Strategy 1: Check common mappings first (fastest)
    common_result = self._check_common_mappings(entity)
    if common_result['confidence'] == 'high':
        return common_result
    
    # Strategy 2: Database discovery (most accurate)
    if self.db:
        db_result = await self._query_database_variations(entity)
        if db_result['confidence'] != 'low':
            return db_result
    
    # Strategy 3: LLM-based intelligent matching (fallback)
    if self.openai_client:
        llm_result = await self._llm_variation_matching(entity)
        if llm_result['confidence'] != 'low':
            return llm_result
    
    # Strategy 4: Return common mappings as last resort
    return common_result

def _check_common_mappings(self, entity: Dict) -> Dict:
    """Check pre-defined common mappings"""
    
    entity_type = entity['type']
    entity_value = entity['value']
    
    if entity_type in self.common_mappings:
        type_mappings = self.common_mappings[entity_type]
        
        # Check if entity value matches any known variations
        for standard_form, variations in type_mappings.items():
            if entity_value.lower() in [v.lower() for v in variations]:
                return {
                    'exact_matches': variations,
                    'likely_matches': [],
                    'confidence': 'high',
                    'source': 'common_mappings',
                    'standard_form': standard_form
                }
    
    return {
        'exact_matches': [entity_value],
        'likely_matches': [],
        'confidence': 'low',
        'source': 'no_mapping'
    }

async def _query_database_variations(self, entity: Dict) -> Dict:
    """Query database for actual data variations"""
    
    table = entity['table']
    column = entity['column'] 
    entity_value = entity['value']
    
    try:
        # Get all distinct values from the relevant column
        discovery_query = f"""
        SELECT DISTINCT {column}, COUNT(*) as frequency
        FROM {table}
        WHERE {column} IS NOT NULL
          AND {column} != ''
        GROUP BY {column}
        HAVING COUNT(*) >= 5  -- Only variations with meaningful frequency
        ORDER BY COUNT(*) DESC
        LIMIT 50;
        """
        
        results = await self.db.execute(discovery_query)
        
        if not results:
            return {'exact_matches': [entity_value], 'confidence': 'low', 'source': 'no_db_data'}
        
        # Analyze results to find variations
        db_values = [row[0] for row in results]
        return await self._analyze_database_variations(entity_value, db_values)
        
    except Exception as e:
        logging.error(f"Database discovery failed for {table}.{column}: {e}")
        return {'exact_matches': [entity_value], 'confidence': 'low', 'source': 'db_error'}

async def _analyze_database_variations(self, entity_value: str, db_values: List[str]) -> Dict:
    """Analyze database values to find variations using multiple techniques"""
    
    exact_matches = []
    likely_matches = []
    fuzzy_matches = []
    
    entity_lower = entity_value.lower()
    entity_upper = entity_value.upper()
    
    for db_value in db_values:
        db_lower = db_value.lower()
        db_upper = db_value.upper()
        
        # Exact match (case insensitive)
        if db_lower == entity_lower:
            exact_matches.append(db_value)
            
        # Abbreviation match (US matches United States)
        elif (entity_upper in db_upper) or (db_upper in entity_upper):
            likely_matches.append(db_value)
            
        # Partial match (contains)
        elif entity_lower in db_lower or db_lower in entity_lower:
            fuzzy_matches.append(db_value)
        
        # Levenshtein distance for typos
        elif self._calculate_similarity(entity_lower, db_lower) > 0.8:
            fuzzy_matches.append(db_value)
    
    # Determine confidence based on match quality
    if exact_matches:
        confidence = 'high'
    elif likely_matches:
        confidence = 'medium'
    elif fuzzy_matches:
        confidence = 'low'
    else:
        confidence = 'none'
        exact_matches = [entity_value]  # At least return original
    
    return {
        'exact_matches': exact_matches,
        'likely_matches': likely_matches[:5],  # Limit for performance
        'fuzzy_matches': fuzzy_matches[:3],
        'confidence': confidence,
        'source': 'database_analysis',
        'total_db_values': len(db_values)
    }

def _calculate_similarity(self, str1: str, str2: str) -> float:
    """Calculate string similarity using simple ratio"""
    if not str1 or not str2:
        return 0.0
    
    # Simple similarity based on common characters
    common_chars = set(str1) & set(str2)
    all_chars = set(str1) | set(str2)
    
    return len(common_chars) / len(all_chars) if all_chars else 0.0
Step 6: LLM-Powered Intelligent Matching
pythonasync def _llm_variation_matching(self, entity: Dict) -> Dict:
    """Use GPT-4o for intelligent variation matching"""
    
    if not self.openai_client:
        return {'exact_matches': [entity['value']], 'confidence': 'low', 'source': 'no_llm'}
    
    # Get database values for context
    db_context = ""
    if self.db:
        try:
            sample_query = f"""
            SELECT DISTINCT {entity['column']}, COUNT(*) as count
            FROM {entity['table']}
            WHERE {entity['column']} IS NOT NULL
            GROUP BY {entity['column']}
            ORDER BY COUNT(*) DESC
            LIMIT 20;
            """
            results = await self.db.execute(sample_query)
            db_values = [f"- {row[0]} (count: {row[1]})" for row in results]
            db_context = f"Available database values:\n" + "\n".join(db_values)
        except:
            db_context = "Database values not available"
    
    matching_prompt = f"""
    Find database values that match the user input for this equity management query.
    
    User Input: "{entity['value']}"
    Entity Type: {entity['type']}
    Context: {entity.get('context_words', [])}
    
    {db_context}
    
    Find matches using these strategies:
    1. Exact match (case-insensitive)
    2. Abbreviation match (US → United States, IT → Information Technology)
    3. Partial match (contains substring)
    4. Semantic match (similar meaning in business context)
    
    Consider these business contexts:
    - Geographic: Countries may have multiple forms (US/USA/United States)
    - Departments: May have formal/informal names (IT/Information Technology)
    - Status: May have synonyms (active/employed/current)
    
    Return JSON format:
    {{
        "exact_matches": ["exact_value"],
        "likely_matches": ["similar_value1", "similar_value2"], 
        "fuzzy_matches": ["maybe_value"],
        "confidence": "high|medium|low",
        "reasoning": "Why these matches were selected"
    }}
    """
    
    try:
        response = await self.openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": matching_prompt}],
            temperature=0.1,
            max_tokens=800
        )
        
        result = json.loads(response.choices[0].message.content)
        result['source'] = 'llm_matching'
        return result
        
    except Exception as e:
        logging.error(f"LLM variation matching failed: {e}")
        return {
            'exact_matches': [entity['value']],
            'confidence': 'low',
            'source': 'llm_error'
        }
Step 7: Discovery Context Assembly
pythondef _build_discovery_context(self, discovery_results: Dict) -> str:
    """Build comprehensive discovery context for GPT-4o"""
    
    if not discovery_results:
        return ""
    
    context_lines = ["\nEntity Discovery Context:"]
    
    for entity_value, matches in discovery_results.items():
        context_lines.append(f"\nFor \"{entity_value}\":")
        
        # Add exact matches
        if matches.get('exact_matches'):
            exact_list = matches['exact_matches'][:5]  # Limit for readability
            context_lines.append(f"  Exact matches: {exact_list}")
            
            # Generate SQL hint
            if len(exact_list) == 1:
                sql_hint = f"WHERE column = '{exact_list[0]}'"
            else:
                sql_hint = f"WHERE column IN ({', '.join([f\"'{v}'\" for v in exact_list])})"
            context_lines.append(f"  SQL Application: {sql_hint}")
        
        # Add likely matches if available
        if matches.get('likely_matches'):
            context_lines.append(f"  Likely matches: {matches['likely_matches'][:3]}")
        
        # Add confidence and source info
        confidence = matches.get('confidence', 'unknown')
        source = matches.get('source', 'unknown')
        context_lines.append(f"  Confidence: {confidence} (source: {source})")
        
        # Add reasoning if available
        if matches.get('reasoning'):
            context_lines.append(f"  Reasoning: {matches['reasoning']}")
    
    # Add summary guidance
    context_lines.append("\nDiscovery Guidance:")
    context_lines.append("- Use exact matches for WHERE clauses when confidence is high")
    context_lines.append("- Include likely matches when confidence is medium")
    context_lines.append("- Apply case-insensitive matching when appropriate")
    
    return "\n".join(context_lines)
📅 Component 2: DateProcessor
Purpose:
Resolves complex date expressions by understanding fiscal calendars, business events, and equity-specific temporal logic.
Step 1: Date Expression Classification
pythonclass DateExpressionType(Enum):
    """Types of date expressions in equity queries"""
    FISCAL = "fiscal"              # Q1, Q2, Q3, Q4, fiscal year
    RELATIVE = "relative"          # next month, last quarter, upcoming
    BUSINESS = "business"          # next vesting, cliff date, exercise window
    COMPLIANCE = "compliance"      # blackout period, earnings window, 10b5-1
    ABSOLUTE = "absolute"          # December 2024, 2025-01-01
    EVENT = "event"               # after IPO, pre-acquisition, post-earnings
Step 2: Date Expression Extraction
pythonclass DateProcessor:
    def __init__(self, db_connection: Optional[Any] = None):
        self.db = db_connection
        self.fiscal_cache = {}
        self.business_calendar_cache = {}
        self.date_patterns = self._load_date_patterns()
    
    def _load_date_patterns(self) -> Dict:
        """Patterns to identify different types of date expressions"""
        return {
            'fiscal': [
                r'\bQ[1-4]\b',                           # Q1, Q2, Q3, Q4
                r'\b(fiscal\s+year|FY)\s*\d{4}?\b',     # fiscal year, FY2024
                r'\b(fiscal\s+quarter)\b'                # fiscal quarter
            ],
            'relative': [
                r'\b(next|last|current|this)\s+(month|quarter|year)\b',    # next month
                r'\b(upcoming|recent|past)\b',                             # upcoming
                r'\b(year.?end|month.?end|quarter.?end)\b'                 # year-end
            ],
            'business': [
                r'\b(next\s+vesting|upcoming\s+vest)\b',                   # next vesting
                r'\b(cliff\s+date|cliff)\b',                              # cliff dates
                r'\b(exercise\s+window|expir)\w*\b',                      # exercise window
                r'\b(grant\s+date|award\s+date)\b'                       # grant dates
            ],
            'compliance': [
                r'\b(blackout\s+period|blackout)\b',                      # blackout periods
                r'\b(earnings\s+window|earnings)\b',                      # earnings windows
                r'\b(trading\s+window|10b5-1)\b',                        # trading plans
                r'\b(insider\s+trading)\b'                               # insider restrictions
            ],
            'absolute': [
                r'\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b',                      # 2024-12-31
                r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b',  # December 2024
                r'\b\d{1,2}[-/]\d{1,2}[-/]\d{4}\b'                      # 12/31/2024
            ],
            'event': [
                r'\b(after|before|during|post|pre).+(IPO|acquisition|merger|spinoff)\b',  # after IPO
                r'\b(earnings\s+announcement|earnings\s+call)\b',         # earnings events
                r'\b(material\s+event|significant\s+event)\b'            # material events
            ]
        }

    async def process_dates(self, user_query: str) -> str:
        """Main date processing pipeline"""
        
        # Step 1: Extract all date expressions
        date_expressions = self._extract_date_expressions(user_query)
        
        if not date_expressions:
            return ""
        
        # Step 2: Resolve each expression with business context
        resolved_dates = {}
        for expr in date_expressions:
            resolved_dates[expr['text']] = await self._resolve_date_expression(expr)
        
        # Step 3: Build comprehensive date context
        return self._build_date_context(resolved_dates, user_query)
    
    def _extract_date_expressions(self, query: str) -> List[Dict]:
        """Extract and classify date expressions"""
        
        expressions = []
        
        for expr_type, patterns in self.date_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, query, re.IGNORECASE)
                for match in matches:
                    expressions.append({
                        'text': match.group(0),
                        'type': expr_type,
                        'start': match.start(),
                        'end': match.end(),
                        'context': self._get_expression_context(query, match.start(), match.end())
                    })
        
        # Remove duplicates and sort by position
        unique_expressions = []
        seen_positions = set()
        
        for expr in sorted(expressions, key=lambda x: x['start']):
            position_key = (expr['start'], expr['end'])
            if position_key not in seen_positions:
                unique_expressions.append(expr)
                seen_positions.add(position_key)
        
        return unique_expressions
    
    def _get_expression_context(self, query: str, start: int, end: int) -> Dict:
        """Get context around date expression for better resolution"""
        
        # Get surrounding words
        words_before = query[:start].split()[-3:] if start > 0 else []
        words_after = query[end:].split()[:3] if end < len(query) else []
        
        return {
            'before': words_before,
            'after': words_after,
            'full_context': ' '.join(words_before + ['<DATE>'] + words_after)
        }
Step 3: Multi-Strategy Date Resolution
pythonasync def _resolve_date_expression(self, expression: Dict) -> Dict:
    """Resolve date expression using appropriate strategy"""
    
    expr_type = expression['type']
    expr_text = expression['text'].lower()
    context = expression['context']
    
    # Route to appropriate resolver
    resolvers = {
        'fiscal': self._resolve_fiscal_date,
        'relative': self._resolve_relative_date,
        'business': self._resolve_business_date,
        'compliance': self._resolve_compliance_date,
        'absolute': self._resolve_absolute_date,
        'event': self._resolve_event_date
    }
    
    resolver = resolvers.get(expr_type, self._resolve_generic_date)
    return await resolver(expression)

async def _resolve_fiscal_date(self, expression: Dict) -> Dict:
    """Resolve fiscal date expressions with company-specific calendars"""
    
    expr_text = expression['text'].lower()
    
    # Get fiscal calendar information
    fiscal_info = await self._get_fiscal_calendar()
    
    if 'q1' in expr_text:
        return await self._calculate_fiscal_quarter(1, fiscal_info)
    elif 'q2' in expr_text:
        return await self._calculate_fiscal_quarter(2, fiscal_info)
    elif 'q3' in expr_text:
        return await self._calculate_fiscal_quarter(3, fiscal_info)
    elif 'q4' in expr_text:
        return await self._calculate_fiscal_quarter(4, fiscal_info)
    elif 'fiscal year' in expr_text or 'fy' in expr_text:
        return {
            'sql': f"BETWEEN '{fiscal_info['fy_start']}' AND '{fiscal_info['fy_end']}'",
            'range_start': fiscal_info['fy_start'],
            'range_end': fiscal_info['fy_end'],
            'description': f"Full fiscal year: {fiscal_info['fy_start']} to {fiscal_info['fy_end']}",
            'fiscal_aware': True
        }
    
    return {'sql': expr_text, 'description': f'Unresolved fiscal date: {expr_text}'}

async def _calculate_fiscal_quarter(self, quarter: int, fiscal_info: Dict) -> Dict:
    """Calculate specific fiscal quarter dates"""
    
    from datetime import datetime, timedelta
    from dateutil.relativedelta import relativedelta
    
    fy_end = datetime.strptime(fiscal_info['fy_end'], '%Y-%m-%d')
    
    # Calculate quarter start/end based on fiscal year end
    quarters = {
        4: {'months_before_fy_end': 0},      # Q4 = last quarter  
        3: {'months_before_fy_end': 3},      # Q3 = 3 months before FY end
        2: {'months_before_fy_end': 6},      # Q2 = 6 months before FY end
        1: {'months_before_fy_end': 9}       # Q1 = 9 months before FY end
    }
    
    months_back = quarters[quarter]['months_before_fy_end']
    quarter_end = fy_end - relativedelta(months=months_back)
    quarter_start = quarter_end - relativedelta(months=3) + timedelta(days=1)
    
    return {
        'sql': f"BETWEEN '{quarter_start.strftime('%Y-%m-%d')}' AND '{quarter_end.strftime('%Y-%m-%d')}'",
        'range_start': quarter_start.strftime('%Y-%m-%d'),
        'range_end': quarter_end.strftime('%Y-%m-%d'),
        'description': f"Fiscal Q{quarter}: {quarter_start.strftime('%Y-%m-%d')} to {quarter_end.strftime('%Y-%m-%d')}",
        'fiscal_aware': True,
        'requires_joins': ['clients.client_latest']  # May need fiscal calendar
    }

async def _resolve_business_date(self, expression: Dict) -> Dict:
    """Resolve equity-specific business date expressions"""
    
    expr_text = expression['text'].lower()
    context = expression['context']
    
    if 'next vesting' in expr_text or 'upcoming vest' in expr_text:
        return {
            'sql': """(SELECT MIN(vs.vesting_date) 
                     FROM vesting_schedules.vesting_schedules vs
                     JOIN grants.tranches t ON vs.tranche_id = t.tranche_id
                     JOIN grants.grant_latest g ON t.grant_id = g.grant_id
                     WHERE g.participant_hub_key = p.participant_hub_key
                     AND vs.vesting_date > CURRENT_DATE)""",
            'description': 'Next vesting date for each participant',
            'requires_joins': [
                'grants.grant_latest',
                'grants.tranches', 
                'vesting_schedules.vesting_schedules'
            ],
            'per_participant': True,
            'filter_logic': 'vs.vesting_date > CURRENT_DATE'
        }
    
    elif 'cliff' in expr_text:
        return {
            'sql': 'g.grant_date + (COALESCE(t.cliff_months, g.cliff_months, 12) * INTERVAL \'1 month\')',
            'description': 'Grant cliff date (grant_date + cliff_months)',
            'requires_joins': ['grants.grant_latest', 'grants.tranches'],
            'business_logic': 'No vesting until cliff date is reached'
        }
    
    elif 'exercise window' in expr_text or 'expir' in expr_text:
        return {
            'sql': 'g.grant_date + INTERVAL \'10 years\'',
            'description': 'Option exercise window expiration (10 years from grant)',
            'requires_joins': ['grants.grant_latest'],
            'filter_logic': 'g.grant_type IN (\'ISO\', \'NQSO\', \'stock_option\')',
            'business_logic': 'Standard 10-year exercise window for stock options'
        }
    
    return {'sql': expr_text, 'description': f'Unresolved business date: {expr_text}'}

async def _resolve_compliance_date(self, expression: Dict) -> Dict:
    """Resolve compliance-related date expressions"""
    
    expr_text = expression['text'].lower()
    
    if 'blackout' in expr_text:
        return {
            'sql': 'pl.blackout_start_date',
            'range_start': 'pl.blackout_start_date',
            'range_end': 'pl.blackout_end_date', 
            'description': 'Trading blackout period',
            'requires_joins': ['participants.participant_legal_detail'],
            'filter_logic': 'CURRENT_DATE BETWEEN pl.blackout_start_date AND pl.blackout_end_date',
            'compliance_context': 'Participants cannot trade during blackout periods'
        }
    
    elif 'earnings' in expr_text:
        # Get earnings calendar
        earnings_info = await self._get_earnings_calendar()
        return {
            'sql': f"'{earnings_info['next_earnings']}'::DATE + INTERVAL '2 days'",
            'description': 'Trading window opens 2 days after earnings announcement',
            'requires_joins': ['clients.earnings_calendar'],
            'compliance_context': 'Trading allowed after earnings plus cooling-off period'
        }
    
    elif '10b5-1' in expr_text or 'trading plan' in expr_text:
        return {
            'sql': 'pl.trading_plan_start_date',
            'range_start': 'pl.trading_plan_start_date',
            'range_end': 'pl.trading_plan_end_date',
            'description': '10b5-1 trading plan effective period',
            'requires_joins': ['participants.participant_legal_detail'],
            'filter_logic': "pl.trading_plan_type = '10b5-1' AND CURRENT_DATE BETWEEN pl.trading_plan_start_date AND pl.trading_plan_end_date",
            'compliance_context': 'Pre-arranged trading plan for insiders'
        }
    
    return {'sql': expr_text, 'description': f'Unresolved compliance date: {expr_text}'}
Step 4: Fiscal Calendar Discovery
pythonasync def _get_fiscal_calendar(self, client_hub_key: str = None) -> Dict:
    """Discover company fiscal calendar from database"""
    
    cache_key = client_hub_key or 'default'
    if cache_key in self.fiscal_cache:
        return self.fiscal_cache[cache_key]
    
    if self.db:
        try:
            # Query fiscal calendar
            if client_hub_key:
                fiscal_query = """
                SELECT fiscal_year_end, fiscal_year_start, client_name
                FROM clients.client_latest
                WHERE client_hub_key = %s
                """
                params = [client_hub_key]
            else:
                # Get most common fiscal calendar
                fiscal_query = """
                SELECT fiscal_year_end, fiscal_year_start, 
                       COUNT(*) as company_count
                FROM clients.client_latest
                WHERE fiscal_year_end IS NOT NULL
                GROUP BY fiscal_year_end, fiscal_year_start
                ORDER BY COUNT(*) DESC
                LIMIT 1
                """
                params = []
            
            result = await self.db.execute(fiscal_query, params)
            
            if result:
                fiscal_info = {
                    'fy_end': result[0][0].strftime('%Y-%m-%d') if result[0][0] else '2024-12-31',
                    'fy_start': result[0][1].strftime('%Y-%m-%d') if result[0][1] else '2024-01-01',
                    'source': 'database',
                    'client_specific': bool(client_hub_key)
                }
                
                self.fiscal_cache[cache_key] = fiscal_info
                return fiscal_info
                
        except Exception as e:
            logging.error(f"Fiscal calendar query failed: {e}")
    
    # Default to calendar year
    default_fiscal = {
        'fy_end': '2024-12-31',
        'fy_start': '2024-01-01',
        'source': 'default',
        'client_specific': False
    }
    
    self.fiscal_cache[cache_key] = default_fiscal
    return default_fiscal

async def _get_earnings_calendar(self) -> Dict:
    """Get earnings announcement dates"""
    
    if 'earnings' in self.business_calendar_cache:
        return self.business_calendar_cache['earnings']
    
    if self.db:
        try:
            earnings_query = """
            SELECT 
                next_earnings_date,
                last_earnings_date,
                earnings_frequency
            FROM clients.earnings_calendar
            WHERE effective_date <= CURRENT_DATE
            AND (end_date IS NULL OR end_date > CURRENT_DATE)
            ORDER BY effective_date DESC
            LIMIT 1
            """
            
            result = await self.db.execute(earnings_query)
            
            if result:
                earnings_info = {
                    'next_earnings': result[0][0].strftime('%Y-%m-%d') if result[0][0] else '2024-12-31',
                    'last_earnings': result[0][1].strftime('%Y-%m-%d') if result[0][1] else '2024-09-30',
                    'frequency': result[0][2] or 'quarterly',
                    'source': 'database'
                }
                
                self.business_calendar_cache['earnings'] = earnings_info
                return earnings_info
                
        except Exception as e:
            logging.error(f"Earnings calendar query failed: {e}")
    
    # Default earnings schedule
    default_earnings = {
        'next_earnings': '2024-12-31',
        'last_earnings': '2024-09-30',
        'frequency': 'quarterly',
        'source': 'default'
    }
    
    self.business_calendar_cache['earnings'] = default_earnings
    return default_earnings
Step 5: Date Context Assembly
pythondef _build_date_context(self, resolved_dates: Dict, original_query: str) -> str:
    """Build comprehensive date context for GPT-4o"""
    
    if not resolved_dates:
        return ""
    
    context_lines = ["\nDate Processing Context:"]
    required_joins = set()
    filter_conditions = []
    business_logic = []
    
    for original_expr, resolution in resolved_dates.items():
        context_lines.append(f"\n'{original_expr}':")
        
        # Add SQL expression
        if 'sql' in resolution:
            context_lines.append(f"  SQL: {resolution['sql']}")
        
        # Add description
        if 'description' in resolution:
            context_lines.append(f"  Description: {resolution['description']}")
        
        # Add date range if available
        if 'range_start' in resolution and 'range_end' in resolution:
            context_lines.append(f"  Date Range: {resolution['range_start']} to {resolution['range_end']}")
        
        # Collect required joins
        if 'requires_joins' in resolution:
            required_joins.update(resolution['requires_joins'])
        
        # Collect filter logic
        if 'filter_logic' in resolution:
            filter_conditions.append(resolution['filter_logic'])
        
        # Collect business logic
        if 'business_logic' in resolution:
            business_logic.append(f"{original_expr}: {resolution['business_logic']}")
        
        # Add special context
        if resolution.get('fiscal_aware'):
            context_lines.append("  Note: Uses company-specific fiscal calendar")
        
        if resolution.get('per_participant'):
            context_lines.append("  Note: Calculated per participant")
        
        if resolution.get('compliance_context'):
            context_lines.append(f"  Compliance: {resolution['compliance_context']}")
    
    # Add summary sections
    if required_joins:
        context_lines.append(f"\nRequired JOINs for date logic: {list(required_joins)}")
    
    if filter_conditions:
        context_lines.append("\nAdditional WHERE conditions:")
        for condition in filter_conditions:
            context_lines.append(f"  - {condition}")
    
    if business_logic:
        context_lines.append("\nBusiness Logic Notes:")
        for logic in business_logic:
            context_lines.append(f"  - {logic}")
    
    # Add usage guidance
    context_lines.extend([
        "\nDate Usage Guidance:",
        "- Apply fiscal calendar logic for Q1-Q4 references",
        "- Use per-participant calculations for vesting dates",
        "- Include compliance filters for trading-related dates",
        "- Handle NULL dates appropriately in calculations"
    ])
    
    return "\n".join(context_lines)
🔄 Phase 3 Integration Process
Step 1: Query Analysis
python# Determine what intelligence features are needed
needs_entity_discovery = QueryClassifier.needs_entity_discovery(user_query)
needs_date_processing = QueryClassifier.needs_date_processing(user_query)

print(f"Entity discovery needed: {needs_entity_discovery}")
print(f"Date processing needed: {needs_date_processing}")
Step 2: Parallel Processing
python# Run discovery and date processing in parallel for performance
async def process_intelligence_layer(user_query: str):
    discovery_task = None
    date_task = None
    
    if needs_entity_discovery:
        discovery_task = entity_discovery.discover_entities(user_query)
    
    if needs_date_processing:
        date_task = date_processor.process_dates(user_query)
    
    # Wait for both to complete
    results = await asyncio.gather(
        discovery_task or asyncio.coroutine(lambda: "")(),
        date_task or asyncio.coroutine(lambda: "")()
    )
    
    return {
        'discovery_context': results[0],
        'date_context': results[1]
    }
Step 3: Context Integration
python# Integrate Phase 3 outputs with other phases
intelligence_results = await process_intelligence_layer(user_query)

complete_prompt = base_template.format(
    schema_section=phase1_schema,           # Phase 1
    business_context=phase1_business,       # Phase 1  
    rules_context=phase2_rules,             # Phase 2
    generation_rules=phase2_generation,     # Phase 2
    discovery_context=intelligence_results['discovery_context'],  # Phase 3
    date_context=intelligence_results['date_context'],           # Phase 3
    # Phase 4 & 5 components...
)
📊 Complete Phase 3 Example
Input: "Show UK officers with next vesting in Q4"
Phase 3 Processing:
Entity Discovery:
python# Detects "UK" as geographic entity
# Queries database: SELECT DISTINCT country_code FROM participant_address
# Finds: ['UK', 'United Kingdom', 'Britain', 'Great Britain', 'GBR']
# LLM confirms: High confidence matches

discovery_context = """
Entity Discovery Context:
For "UK": Exact matches: ['UK', 'United Kingdom', 'Britain', 'Great Britain']
SQL Application: WHERE country_code IN ('UK', 'United Kingdom', 'Britain', 'Great Britain')
Confidence: high (source: database_analysis)
"""
Date Processing:
python# Detects "Q4" as fiscal date and "next vesting" as business date
# Queries fiscal calendar: fiscal_year_end = '2024-03-31'
# Calculates Q4 = Jan-Mar 2024 for this fiscal year
# Resolves "next vesting" as participant-specific MIN(vesting_date)

date_context = """
Date Processing Context:
'Q4': 
  SQL: BETWEEN '2024-01-01' AND '2024-03-31'
  Description: Fiscal Q4: 2024-01-01 to 2024-03-31
  Note: Uses company-specific fiscal calendar

'next vesting':
  SQL: (SELECT MIN(vs.vesting_date) FROM vesting_schedules.vesting_schedules vs ...)
  Description: Next vesting date for each participant
  Note: Calculated per participant

Required JOINs for date logic: ['clients.client_latest', 'grants.grant_latest', 'grants.tranches', 'vesting_schedules.vesting_schedules']
"""
Phase 3 Success Criteria

Entity Discovery Accuracy:

python   assert "UK" in discovered_entities
   assert len(discovered_entities["UK"]["exact_matches"]) > 1
   assert discovered_entities["UK"]["confidence"] == "high"

Date Resolution Completeness:

python   assert "Q4" in resolved_dates
   assert "fiscal" in resolved_dates["Q4"]["description"].lower()
   assert resolved_dates["Q4"]["range_start"] != resolved_dates["Q4"]["range_end"]

Context Quality:

python   assert "Entity Discovery Context:" in final_context
   assert "Date Processing Context:" in final_context  
   assert "Required JOINs" in final_context
🚀 Phase 3 Deliverables
At the end of Phase 3, you have:

EntityDiscovery class - Multi-strategy entity variation discovery
DateProcessor class - Fiscal-aware date expression resolution
Database integration - Live data variation discovery
LLM integration - Intelligent matching and validation
Caching system - Performance optimization for repeated queries
Context assembly - Rich context for GPT-4o consumption
Error handling - Graceful fallbacks when discovery fails
Business awareness - Understanding of equity-specific temporal logic

Phase 3 transforms rigid pattern matching into intelligent, adaptive query understanding that handles the messy reality of user language and database inconsistencies!
