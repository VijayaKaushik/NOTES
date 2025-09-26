 Phase 4 Overview
Phase 4: Optimization adds performance intelligence and pattern recognition to generate efficient, well-structured SQL:

JOIN Optimization → Smart table requirement analysis and JOIN path optimization
QueryPatterns → Template library of common equity query structures and best practices

This phase ensures GPT-4o generates not just correct SQL, but performant and maintainable SQL.
🔗 Component 1: JOIN Optimization System
Purpose:
Automatically determines the minimum set of required table JOINs based on business rules, discovered entities, and date requirements. Prevents unnecessary JOINs while ensuring all needed data is accessible.
Step 1: JOIN Requirement Analysis Engine
pythonclass JoinRequirementAnalyzer:
    """Analyzes query components to determine optimal JOIN strategy"""
    
    def __init__(self, business_rules_manager, schema_manager):
        self.business_rules = business_rules_manager
        self.schema_manager = schema_manager
        self.join_graph = self._build_join_graph()
        self.performance_weights = self._load_performance_weights()
    
    def _build_join_graph(self) -> Dict:
        """Build graph of table relationships for path optimization"""
        
        return {
            # Core hub-key relationships
            'participants.participant_detail': {
                'connects_to': [
                    'participants.participant_address',
                    'participants.participant_employer_detail', 
                    'participants.participant_legal_detail',
                    'grants.grant_latest'
                ],
                'join_key': 'participant_hub_key',
                'cardinality': '1:many',
                'performance_weight': 1  # Lightweight table
            },
            'clients.client_latest': {
                'connects_to': [
                    'plans.plans',
                    'participants.participant_employer_detail'
                ],
                'join_key': 'client_hub_key', 
                'cardinality': '1:many',
                'performance_weight': 1
            },
            'grants.grant_latest': {
                'connects_to': [
                    'grants.tranches',
                    'participants.participant_detail',
                    'plans.plans'
                ],
                'join_key': 'grant_id',
                'cardinality': '1:many',
                'performance_weight': 3  # Larger table
            },
            'grants.tranches': {
                'connects_to': [
                    'vesting_schedules.vesting_schedules',
                    'grants.grant_latest'
                ],
                'join_key': 'tranche_id',
                'cardinality': '1:many', 
                'performance_weight': 2
            },
            'vesting_schedules.vesting_schedules': {
                'connects_to': [
                    'grants.tranches'
                ],
                'join_key': 'tranche_id',
                'cardinality': 'many:1',
                'performance_weight': 4  # Largest table - many rows per grant
            }
        }
    
    def _load_performance_weights(self) -> Dict:
        """Performance characteristics of different JOIN patterns"""
        return {
            'hub_key_joins': 0.1,      # Very fast - indexed
            'foreign_key_joins': 0.2,  # Fast - indexed  
            'cross_schema_joins': 0.5, # Moderate - network overhead
            'large_table_joins': 1.0,  # Expensive - lots of data
            'vesting_schedule_joins': 2.0  # Most expensive - largest tables
        }
Step 2: Smart JOIN Path Discovery
pythondef analyze_join_requirements(self, query_components: Dict) -> Dict:
    """Analyze all query components to determine JOIN requirements"""
    
    required_tables = set()
    join_reasons = {}
    performance_impact = 0
    
    # Analyze business rules requirements
    if query_components.get('rules_context'):
        rules_joins = self.business_rules.get_required_joins(
            query_components['query_type']
        )
        required_tables.update(rules_joins)
        join_reasons['business_rules'] = list(rules_joins)
    
    # Analyze entity discovery requirements
    if query_components.get('discovery_context'):
        discovery_joins = self._extract_discovery_joins(
            query_components['discovery_context']
        )
        required_tables.update(discovery_joins)
        join_reasons['entity_discovery'] = list(discovery_joins)
    
    # Analyze date processing requirements
    if query_components.get('date_context'):
        date_joins = self._extract_date_joins(
            query_components['date_context']
        )
        required_tables.update(date_joins)
        join_reasons['date_processing'] = list(date_joins)
    
    # Find optimal JOIN path
    join_path = self._find_optimal_join_path(required_tables)
    
    # Calculate performance impact
    performance_impact = self._calculate_performance_impact(join_path)
    
    return {
        'required_tables': list(required_tables),
        'optimal_join_path': join_path,
        'join_reasons': join_reasons,
        'performance_impact': performance_impact,
        'optimization_notes': self._generate_optimization_notes(join_path)
    }

def _extract_discovery_joins(self, discovery_context: str) -> Set[str]:
    """Extract table requirements from entity discovery context"""
    
    joins = set()
    
    # Geographic entities typically need address table
    if 'country' in discovery_context.lower() or 'region' in discovery_context.lower():
        joins.add('participants.participant_address')
    
    # Organizational entities need employer detail
    if 'department' in discovery_context.lower() or 'division' in discovery_context.lower():
        joins.add('participants.participant_employer_detail')
    
    # Always need core participant table for joins
    if joins:
        joins.add('participants.participant_detail')
    
    return joins

def _extract_date_joins(self, date_context: str) -> Set[str]:
    """Extract table requirements from date processing context"""
    
    joins = set()
    
    # Fiscal dates need client calendar
    if 'fiscal' in date_context.lower() or 'Q1' in date_context or 'Q2' in date_context:
        joins.add('clients.client_latest')
    
    # Vesting dates need vesting tables
    if 'vesting' in date_context.lower():
        joins.update([
            'grants.grant_latest',
            'grants.tranches', 
            'vesting_schedules.vesting_schedules'
        ])
    
    # Compliance dates need legal detail
    if 'blackout' in date_context.lower() or '10b5-1' in date_context.lower():
        joins.add('participants.participant_legal_detail')
    
    return joins

def _find_optimal_join_path(self, required_tables: Set[str]) -> List[Dict]:
    """Find the most efficient JOIN path connecting all required tables"""
    
    if not required_tables:
        return []
    
    # Start with core tables that are natural starting points
    core_tables = [
        'participants.participant_detail',
        'clients.client_latest',
        'grants.grant_latest'
    ]
    
    # Find best starting point
    start_table = None
    for core_table in core_tables:
        if core_table in required_tables:
            start_table = core_table
            break
    
    if not start_table:
        start_table = list(required_tables)[0]  # Fallback to first required table
    
    # Build JOIN path using graph traversal
    join_path = []
    connected_tables = {start_table}
    remaining_tables = required_tables - connected_tables
    
    while remaining_tables:
        best_join = self._find_best_next_join(connected_tables, remaining_tables)
        
        if not best_join:
            # No path found - add disconnected table with warning
            disconnected = remaining_tables.pop()
            join_path.append({
                'table': disconnected,
                'join_type': 'CROSS JOIN',  # Not ideal, but necessary
                'join_condition': f'-- Warning: No direct relationship to {disconnected}',
                'performance_warning': True
            })
            connected_tables.add(disconnected)
        else:
            join_path.append(best_join)
            connected_tables.add(best_join['table'])
            remaining_tables.remove(best_join['table'])
    
    return join_path

def _find_best_next_join(self, connected_tables: Set[str], remaining_tables: Set[str]) -> Optional[Dict]:
    """Find the best next table to JOIN based on performance and relationships"""
    
    best_join = None
    best_score = float('inf')
    
    for table in remaining_tables:
        for connected_table in connected_tables:
            # Check if there's a direct relationship
            relationship = self._get_table_relationship(connected_table, table)
            
            if relationship:
                # Calculate join score (lower is better)
                performance_weight = self.join_graph.get(table, {}).get('performance_weight', 1)
                relationship_strength = relationship['strength']  # 0-1, higher is better
                
                score = performance_weight / relationship_strength
                
                if score < best_score:
                    best_score = score
                    best_join = {
                        'table': table,
                        'join_type': relationship['join_type'],
                        'join_condition': relationship['join_condition'],
                        'from_table': connected_table,
                        'performance_weight': performance_weight
                    }
    
    return best_join

def _get_table_relationship(self, table1: str, table2: str) -> Optional[Dict]:
    """Get relationship information between two tables"""
    
    # Define known relationships with JOIN conditions
    relationships = {
        ('participants.participant_detail', 'participants.participant_address'): {
            'join_type': 'LEFT JOIN',
            'join_condition': 'p.participant_hub_key = pa.participant_hub_key',
            'strength': 1.0,  # Strong relationship
            'cardinality': '1:many'
        },
        ('participants.participant_detail', 'participants.participant_legal_detail'): {
            'join_type': 'LEFT JOIN', 
            'join_condition': 'p.participant_hub_key = pl.participant_hub_key',
            'strength': 1.0,
            'cardinality': '1:1'
        },
        ('participants.participant_detail', 'grants.grant_latest'): {
            'join_type': 'LEFT JOIN',
            'join_condition': 'p.participant_hub_key = g.participant_hub_key', 
            'strength': 1.0,
            'cardinality': '1:many'
        },
        ('grants.grant_latest', 'grants.tranches'): {
            'join_type': 'LEFT JOIN',
            'join_condition': 'g.grant_id = t.grant_id',
            'strength': 1.0,
            'cardinality': '1:many'
        },
        ('grants.tranches', 'vesting_schedules.vesting_schedules'): {
            'join_type': 'LEFT JOIN',
            'join_condition': 't.tranche_id = vs.tranche_id',
            'strength': 1.0,
            'cardinality': '1:many'
        },
        ('clients.client_latest', 'plans.plans'): {
            'join_type': 'LEFT JOIN',
            'join_condition': 'c.client_hub_key = pl.client_hub_key',
            'strength': 1.0,
            'cardinality': '1:many'
        }
    }
    
    # Check both directions
    key = (table1, table2)
    reverse_key = (table2, table1)
    
    if key in relationships:
        return relationships[key]
    elif reverse_key in relationships:
        # Reverse the relationship
        rel = relationships[reverse_key]
        return {
            'join_type': rel['join_type'],
            'join_condition': self._reverse_join_condition(rel['join_condition']),
            'strength': rel['strength'],
            'cardinality': self._reverse_cardinality(rel['cardinality'])
        }
    
    return None

def _generate_optimization_notes(self, join_path: List[Dict]) -> List[str]:
    """Generate performance optimization notes for the JOIN path"""
    
    notes = []
    
    # Analyze performance characteristics
    total_weight = sum(join.get('performance_weight', 1) for join in join_path)
    
    if total_weight > 5:
        notes.append("High performance impact query - consider adding WHERE clauses early")
    
    # Check for vesting schedule joins
    vesting_joins = [j for j in join_path if 'vesting_schedules' in j.get('table', '')]
    if vesting_joins:
        notes.append("Vesting schedule JOIN detected - ensure date range filtering")
    
    # Check for cross-schema joins
    schemas = set()
    for join in join_path:
        if 'table' in join:
            schema = join['table'].split('.')[0]
            schemas.add(schema)
    
    if len(schemas) > 2:
        notes.append(f"Multi-schema query ({len(schemas)} schemas) - network latency possible")
    
    # Check for potential Cartesian products
    many_to_many_joins = [j for j in join_path if 'many' in j.get('cardinality', '')]
    if len(many_to_many_joins) > 1:
        notes.append("Multiple 1:many JOINs - verify result set size expectations")
    
    return notes
Step 3: JOIN Context Generation
pythondef build_join_context(self, join_analysis: Dict) -> str:
    """Build comprehensive JOIN context for GPT-4o"""
    
    if not join_analysis['required_tables']:
        return "\nNo additional JOINs required for this query."
    
    context_lines = ["\n## Required JOINs Analysis:"]
    
    # List required tables with reasons
    context_lines.append(f"\n**Required Tables:** {', '.join(join_analysis['required_tables'])}")
    
    # Break down requirements by source
    if join_analysis['join_reasons']:
        context_lines.append("\n**JOIN Requirements by Source:**")
        for source, tables in join_analysis['join_reasons'].items():
            if tables:
                context_lines.append(f"- {source.replace('_', ' ').title()}: {', '.join(tables)}")
    
    # Provide optimal JOIN path
    if join_analysis['optimal_join_path']:
        context_lines.append("\n**Recommended JOIN Path:**")
        context_lines.append("```sql")
        context_lines.append("FROM participants.participant_detail p  -- Start with core table")
        
        for i, join in enumerate(join_analysis['optimal_join_path']):
            alias = self._get_table_alias(join['table'])
            join_condition = join.get('join_condition', '-- condition needed')
            
            context_lines.append(f"{join.get('join_type', 'LEFT JOIN')} {join['table']} {alias}")
            context_lines.append(f"  ON {join_condition}")
        
        context_lines.append("```")
    
    # Add performance guidance
    context_lines.append(f"\n**Performance Impact:** {join_analysis['performance_impact']:.1f}/10")
    
    if join_analysis['optimization_notes']:
        context_lines.append("\n**Optimization Notes:**")
        for note in join_analysis['optimization_notes']:
            context_lines.append(f"- {note}")
    
    # Add JOIN best practices
    context_lines.extend([
        "\n**JOIN Best Practices:**",
        "- Use LEFT JOIN to preserve all participants even if related data is missing",
        "- Apply WHERE clause filters early to reduce JOIN overhead", 
        "- Use table aliases consistently (p, pa, pl, g, t, vs)",
        "- Consider using EXISTS instead of JOIN when only checking for existence"
    ])
    
    return "\n".join(context_lines)

def _get_table_alias(self, table_name: str) -> str:
    """Get consistent table aliases"""
    
    alias_map = {
        'participants.participant_detail': 'p',
        'participants.participant_address': 'pa', 
        'participants.participant_employer_detail': 'pe',
        'participants.participant_legal_detail': 'pl',
        'clients.client_latest': 'c',
        'plans.plans': 'plans',
        'grants.grant_latest': 'g',
        'grants.tranches': 't',
        'vesting_schedules.vesting_schedules': 'vs'
    }
    
    return alias_map.get(table_name, table_name.split('.')[-1][0])
🎯 Component 2: QueryPatterns Library
Purpose:
Provides GPT-4o with a comprehensive library of proven SQL query patterns for common equity scenarios. Each pattern includes business context, performance optimizations, and variations.
Step 1: Pattern Classification System
pythonclass QueryPatternType(Enum):
    """Types of equity query patterns"""
    VESTING = "vesting"                    # Vesting schedules and calculations
    COMPLIANCE = "compliance"              # Regulatory and legal queries  
    REGIONAL = "regional"                  # Geographic breakdowns
    FINANCIAL = "financial"                # Calculations and valuations
    ADMINISTRATIVE = "administrative"       # User management, accounts
    REPORTING = "reporting"                # Executive and management reports
    AUDIT = "audit"                        # Audit trail and compliance tracking
Step 2: Pattern Template Engine
pythonclass QueryPatterns:
    """Comprehensive library of equity query patterns"""
    
    def __init__(self, patterns_file_path: Path = Path("src/rules/prompts/query_patterns.md")):
        self.patterns_file_path = patterns_file_path
        self.pattern_templates = self._load_pattern_templates()
        self.performance_optimizations = self._load_performance_patterns()
    
    def _load_pattern_templates(self) -> Dict:
        """Load comprehensive query pattern templates"""
        
        return {
            'vesting': {
                'basic_vesting_lookup': {
                    'name': 'Basic Vesting Schedule Lookup',
                    'description': 'Find vesting events for participants in a date range',
                    'use_cases': ['next vesting', 'upcoming vesting', 'vesting in period'],
                    'sql_template': '''
                    -- Pattern: Basic Vesting Lookup
                    SELECT 
                        p.participant_name,
                        g.grant_date,
                        vs.vesting_date,
                        vs.vested_shares,
                        vs.cumulative_vested_shares
                    FROM participants.participant_detail p
                    JOIN grants.grant_latest g ON p.participant_hub_key = g.participant_hub_key
                    JOIN grants.tranches t ON g.grant_id = t.grant_id
                    JOIN vesting_schedules.vesting_schedules vs ON t.tranche_id = vs.tranche_id
                    WHERE vs.vesting_date BETWEEN [start_date] AND [end_date]
                      AND p.status = 'active'
                    ORDER BY vs.vesting_date, p.participant_name;
                    ''',
                    'variations': {
                        'next_vesting_per_participant': '''
                        -- Variation: Next vesting date per participant
                        SELECT 
                            p.participant_name,
                            MIN(vs.vesting_date) as next_vesting_date,
                            SUM(vs.vested_shares) as shares_vesting
                        FROM participants.participant_detail p
                        JOIN grants.grant_latest g ON p.participant_hub_key = g.participant_hub_key
                        JOIN grants.tranches t ON g.grant_id = t.grant_id
                        JOIN vesting_schedules.vesting_schedules vs ON t.tranche_id = vs.tranche_id
                        WHERE vs.vesting_date > CURRENT_DATE
                          AND p.status = 'active'
                        GROUP BY p.participant_hub_key, p.participant_name
                        ORDER BY next_vesting_date;
                        ''',
                        'vested_amount_calculation': '''
                        -- Variation: Calculate current vested amounts
                        SELECT 
                            p.participant_name,
                            g.grant_type,
                            g.grant_amount as total_granted,
                            SUM(CASE 
                                WHEN vs.vesting_date <= CURRENT_DATE 
                                THEN vs.vested_shares 
                                ELSE 0 
                            END) as currently_vested,
                            ROUND(
                                SUM(CASE WHEN vs.vesting_date <= CURRENT_DATE THEN vs.vested_shares ELSE 0 END) * 100.0 / g.grant_amount, 
                                2
                            ) as vested_percentage
                        FROM participants.participant_detail p
                        JOIN grants.grant_latest g ON p.participant_hub_key = g.participant_hub_key
                        JOIN grants.tranches t ON g.grant_id = t.grant_id
                        JOIN vesting_schedules.vesting_schedules vs ON t.tranche_id = vs.tranche_id
                        GROUP BY p.participant_hub_key, p.participant_name, g.grant_id, g.grant_type, g.grant_amount
                        HAVING currently_vested > 0
                        ORDER BY vested_percentage DESC;
                        '''
                    },
                    'performance_notes': [
                        'Index on (vesting_date, participant_hub_key) critical for performance',
                        'Use date range filters in WHERE clause before JOINs when possible',
                        'Consider partitioning vesting_schedules by year for large datasets'
                    ],
                    'business_notes': [
                        'Always filter for active participants unless specifically querying terminated',
                        'Vesting calculations should handle partial vesting (cliff periods)',
                        'Consider time zone implications for vesting_date comparisons'
                    ]
                },
                
                'cliff_analysis': {
                    'name': 'Grant Cliff Date Analysis',
                    'description': 'Analyze grants approaching or past cliff dates',
                    'use_cases': ['cliff dates', 'approaching cliff', 'post-cliff analysis'],
                    'sql_template': '''
                    -- Pattern: Cliff Date Analysis
                    WITH cliff_analysis AS (
                        SELECT 
                            p.participant_name,
                            p.employee_type,
                            g.grant_date,
                            g.grant_amount,
                            g.grant_date + (COALESCE(t.cliff_months, g.cliff_months, 12) * INTERVAL '1 month') as cliff_date,
                            CASE 
                                WHEN CURRENT_DATE < g.grant_date + (COALESCE(t.cliff_months, g.cliff_months, 12) * INTERVAL '1 month') 
                                THEN 'Pre-Cliff'
                                ELSE 'Post-Cliff'
                            END as cliff_status,
                            CURRENT_DATE - (g.grant_date + (COALESCE(t.cliff_months, g.cliff_months, 12) * INTERVAL '1 month')) as days_since_cliff
                        FROM participants.participant_detail p
                        JOIN grants.grant_latest g ON p.participant_hub_key = g.participant_hub_key
                        JOIN grants.tranches t ON g.grant_id = t.grant_id
                        WHERE p.status = 'active'
                    )
                    SELECT *
                    FROM cliff_analysis
                    WHERE [cliff_filter_condition]  -- e.g., cliff_date BETWEEN now and +60 days
                    ORDER BY cliff_date;
                    ''',
                    'performance_notes': [
                        'CTE approach allows for complex cliff calculations without repetition',
                        'Index on (grant_date, cliff_months) helpful for cliff calculations'
                    ]
                }
            },
            
            'compliance': {
                'officer_identification': {
                    'name': 'Officer and Insider Identification',
                    'description': 'Identify officers and insiders for compliance purposes',
                    'use_cases': ['officers', 'section 16 officers', '10b5-1 eligible', 'insiders'],
                    'sql_template': '''
                    -- Pattern: Officer and Insider Identification
                    SELECT 
                        p.participant_name,
                        p.employee_type,
                        pl.is_section16_officer,
                        pl.ownership_percentage,
                        CASE 
                            WHEN p.employee_type IN ('ceo', 'cfo', 'director') 
                              OR pl.ownership_percentage >= 10 
                            THEN 'Section 16 Officer'
                            WHEN p.employee_type IN ('officer', 'executive') 
                            THEN 'Officer'
                            ELSE 'Employee'
                        END as compliance_classification,
                        pl.trading_plan_type,
                        pl.blackout_start_date,
                        pl.blackout_end_date,
                        CASE 
                            WHEN CURRENT_DATE BETWEEN COALESCE(pl.blackout_start_date, '1900-01-01') 
                                                 AND COALESCE(pl.blackout_end_date, '1900-01-01')
                            THEN 'In Blackout'
                            ELSE 'Trading Allowed'
                        END as current_trading_status
                    FROM participants.participant_detail p
                    LEFT JOIN participants.participant_legal_detail pl 
                        ON p.participant_hub_key = pl.participant_hub_key
                    WHERE p.status = 'active'
                      AND [officer_filter_conditions]  -- Apply specific officer criteria
                    ORDER BY pl.ownership_percentage DESC, p.employee_type;
                    ''',
                    'variations': {
                        '10b51_eligibility': '''
                        -- Variation: 10b5-1 Plan Eligibility Analysis
                        SELECT 
                            p.participant_name,
                            p.employee_type,
                            pl.ownership_percentage,
                            pl.last_material_info_date,
                            CASE 
                                WHEN p.employee_type IN ('officer', 'executive', 'director')
                                 AND (pl.last_material_info_date IS NULL 
                                      OR pl.last_material_info_date < CURRENT_DATE - INTERVAL '6 months')
                                 AND pl.trading_plan_type IS NULL
                                THEN 'Eligible for 10b5-1'
                                WHEN pl.trading_plan_type = '10b5-1'
                                THEN 'Already has 10b5-1 plan'
                                ELSE 'Not eligible'
                            END as eligibility_status,
                            pl.trading_plan_start_date,
                            pl.trading_plan_end_date
                        FROM participants.participant_detail p
                        JOIN participants.participant_legal_detail pl 
                            ON p.participant_hub_key = pl.participant_hub_key
                        WHERE p.status = 'active'
                          AND p.employee_type IN ('officer', 'executive', 'director')
                        ORDER BY eligibility_status, p.participant_name;
                        '''
                    }
                },
                
                'blackout_period_analysis': {
                    'name': 'Trading Blackout Period Analysis',
                    'description': 'Analyze current and upcoming blackout periods',
                    'use_cases': ['blackout periods', 'trading restrictions', 'compliance windows'],
                    'sql_template': '''
                    -- Pattern: Blackout Period Analysis
                    SELECT 
                        p.participant_name,
                        p.employee_type,
                        pl.blackout_start_date,
                        pl.blackout_end_date,
                        pl.blackout_reason,
                        CASE 
                            WHEN CURRENT_DATE < pl.blackout_start_date 
                            THEN 'Upcoming Blackout'
                            WHEN CURRENT_DATE BETWEEN pl.blackout_start_date AND pl.blackout_end_date 
                            THEN 'Currently in Blackout'
                            WHEN CURRENT_DATE > pl.blackout_end_date 
                            THEN 'Past Blackout'
                            ELSE 'No Blackout'
                        END as blackout_status,
                        CASE 
                            WHEN CURRENT_DATE < pl.blackout_start_date 
                            THEN pl.blackout_start_date - CURRENT_DATE
                            WHEN CURRENT_DATE BETWEEN pl.blackout_start_date AND pl.blackout_end_date 
                            THEN pl.blackout_end_date - CURRENT_DATE
                            ELSE NULL
                        END as days_until_change
                    FROM participants.participant_detail p
                    JOIN participants.participant_legal_detail pl 
                        ON p.participant_hub_key = pl.participant_hub_key
                    WHERE p.status = 'active'
                      AND pl.blackout_start_date IS NOT NULL
                      AND [blackout_filter_conditions]
                    ORDER BY pl.blackout_start_date;
                    '''
                }
            },
            
            'regional': {
                'geographic_breakdown': {
                    'name': 'Geographic Distribution Analysis',
                    'description': 'Break down participants and grants by geographic regions',
                    'use_cases': ['by region', 'by country', 'regional analysis', 'geographic distribution'],
                    'sql_template': '''
                    -- Pattern: Geographic Distribution Analysis  
                    SELECT 
                        pa.country_code,
                        pa.region_code,
                        COUNT(DISTINCT p.participant_hub_key) as participant_count,
                        COUNT(DISTINCT g.grant_id) as total_grants,
                        SUM(g.grant_amount) as total_shares_granted,
                        SUM(CASE 
                            WHEN vs.vesting_date <= CURRENT_DATE 
                            THEN vs.vested_shares 
                            ELSE 0 
                        END) as total_vested_shares,
                        ROUND(
                            AVG(CASE 
                                WHEN g.grant_amount > 0 
                                THEN (SUM(CASE WHEN vs.vesting_date <= CURRENT_DATE THEN vs.vested_shares ELSE 0 END) * 100.0 / g.grant_amount)
                                ELSE 0 
                            END), 
                            2
                        ) as avg_vested_percentage
                    FROM participants.participant_detail p
                    JOIN participants.participant_address pa 
                        ON p.participant_hub_key = pa.participant_hub_key
                    LEFT JOIN grants.grant_latest g 
                        ON p.participant_hub_key = g.participant_hub_key
                    LEFT JOIN grants.tranches t 
                        ON g.grant_id = t.grant_id
                    LEFT JOIN vesting_schedules.vesting_schedules vs 
                        ON t.tranche_id = vs.tranche_id
                    WHERE p.status = 'active'
                      AND pa.end_date IS NULL  -- Current address only
                      AND [geographic_filter_conditions]
                    GROUP BY pa.country_code, pa.region_code
                    ORDER BY participant_count DESC, total_shares_granted DESC;
                    ''',
                    'performance_notes': [
                        'Consider pre-aggregating geographic data for large datasets',
                        'Index on (country_code, region_code, end_date) essential'
                    ]
                }
            },
            
            'financial': {
                'exercise_value_calculation': {
                    'name': 'Option Exercise Value Calculation',
                    'description': 'Calculate exercise values and gains for stock options',
                    'use_cases': ['exercise value', 'option value', 'gains calculation'],
                    'sql_template': '''
                    -- Pattern: Exercise Value Calculation
                    WITH current_valuations AS (
                        SELECT 
                            client_hub_key,
                            current_stock_price,
                            valuation_date
                        FROM clients.current_valuations cv1
                        WHERE cv1.valuation_date = (
                            SELECT MAX(cv2.valuation_date) 
                            FROM clients.current_valuations cv2 
                            WHERE cv2.client_hub_key = cv1.client_hub_key
                        )
                    ),
                    vested_options AS (
                        SELECT 
                            p.participant_hub_key,
                            p.participant_name,
                            g.grant_id,
                            g.exercise_price,
                            SUM(CASE 
                                WHEN vs.vesting_date <= CURRENT_DATE 
                                THEN vs.vested_shares 
                                ELSE 0 
                            END) as vested_shares
                        FROM participants.participant_detail p
                        JOIN grants.grant_latest g ON p.participant_hub_key = g.participant_hub_key
                        JOIN grants.tranches t ON g.grant_id = t.grant_id
                        JOIN vesting_schedules.vesting_schedules vs ON t.tranche_id = vs.tranche_id
                        WHERE g.grant_type IN ('ISO', 'NQSO', 'stock_option')
                          AND g.exercise_price IS NOT NULL
                        GROUP BY p.participant_hub_key, p.participant_name, g.grant_id, g.exercise_price
                        HAVING SUM(CASE WHEN vs.vesting_date <= CURRENT_DATE THEN vs.vested_shares ELSE 0 END) > 0
                    )
                    SELECT 
                        vo.participant_name,
                        vo.exercise_price,
                        cv.current_stock_price,
                        vo.vested_shares,
                        GREATEST(0, (cv.current_stock_price - vo.exercise_price)) as gain_per_share,
                        GREATEST(0, (cv.current_stock_price - vo.exercise_price) * vo.vested_shares) as total_exercise_value,
                        CASE 
                            WHEN cv.current_stock_price > vo.exercise_price 
                            THEN 'In the Money'
                            WHEN cv.current_stock_price = vo.exercise_price 
                            THEN 'At the Money'
                            ELSE 'Underwater'
                        END as option_status
                    FROM vested_options vo
                    JOIN participants.participant_employer_detail pe 
                        ON vo.participant_hub_key = pe.participant_hub_key
                    JOIN current_valuations cv 
                        ON pe.client_hub_key = cv.client_hub_key
                    WHERE [financial_filter_conditions]
                    ORDER BY total_exercise_value DESC;
                    '''
                }
            }
        }
    
    def _load_performance_patterns(self) -> Dict:
        """Load performance optimization patterns"""
        
        return {
            'index_usage': {
                'vesting_queries': [
                    'CREATE INDEX idx_vesting_date_participant ON vesting_schedules.vesting_schedules(vesting_date, participant_hub_key)',
                    'CREATE INDEX idx_participant_status ON participants.participant_detail(status, termination_date)'
                ],
                'compliance_queries': [
                    'CREATE INDEX idx_employee_type ON participants.participant_detail(employee_type)',
                    'CREATE INDEX idx_blackout_dates ON participants.participant_legal_detail(blackout_start_date, blackout_end_date)'
                ]
            },
            'query_optimization': {
                'early_filtering': 'Apply WHERE clauses on indexed columns before JOINs',
                'exists_vs_join': 'Use EXISTS instead of JOIN when only checking for existence',
                'cte_usage': 'Use CTEs for complex calculations to improve readability and performance'
            }
        }
Step 3: Smart Pattern Matching
pythondef get_relevant_patterns(self, query_components: Dict) -> str:
    """Get relevant query patterns based on query characteristics"""
    
    query_text = query_components.get('original_query', '').lower()
    query_type = query_components.get('query_type', 'general')
    
    relevant_patterns = []
    
    # Match patterns based on query content
    if any(word in query_text for word in ['vesting', 'vest', 'cliff']):
        relevant_patterns.extend(self._get_vesting_patterns(query_text))
    
    if any(word in query_text for word in ['officer', 'compliance', 'blackout', '10b5-1']):
        relevant_patterns.extend(self._get_compliance_patterns(query_text))
    
    if any(word in query_text for word in ['region', 'country', 'geographic']):
        relevant_patterns.extend(self._get_regional_patterns(query_text))
    
    if any(word in query_text for word in ['value', 'exercise', 'gain', 'price']):
        relevant_patterns.extend(self._get_financial_patterns(query_text))
    
    # If no specific patterns found, include general patterns
    if not relevant_patterns:
        relevant_patterns = self._get_general_patterns()
    
    return self._format_patterns_for_prompt(relevant_patterns)

def _get_vesting_patterns(self, query_text: str) -> List[Dict]:
    """Get vesting-specific patterns"""
    
    patterns = []
    
    if 'next vesting' in query_text or 'upcoming' in query_text:
        patterns.append(self.pattern_templates['vesting']['basic_vesting_lookup'])
    
    if 'cliff' in query_text:
        patterns.append(self.pattern_templates['vesting']['cliff_analysis'])
    
    return patterns

def _format_patterns_for_prompt(self, patterns: List[Dict]) -> str:
    """Format patterns for GPT-4o consumption"""
    
    if not patterns:
        return ""
    
    formatted_sections = ["\n## Relevant Query Patterns:"]
    
    for i, pattern in enumerate(patterns[:3], 1):  # Limit to top 3 patterns
        formatted_sections.append(f"\n**Pattern {i}: {pattern['name']}**")
        formatted_sections.append(f"Use for: {', '.join(pattern['use_cases'])}")
        formatted_sections.append(f"Description: {pattern['description']}")
        
        # Add main SQL template
        formatted_sections.append("```sql")
        formatted_sections.append(pattern['sql_template'].strip())
        formatted_sections.append("```")
        
        # Add key variations if available
        if 'variations' in pattern:
            formatted_sections.append("**Key Variations:**")
            for var_name, var_sql in list(pattern['variations'].items())[:2]:  # Max 2 variations
                formatted_sections.append(f"- {var_name.replace('_', ' ').title()}")
                formatted_sections.append("```sql")
                formatted_sections.append(var_sql.strip())
                formatted_sections.append("```")
        
        # Add performance notes
        if 'performance_notes' in pattern:
            formatted_sections.append("**Performance Notes:**")
            for note in pattern['performance_notes'][:2]:  # Max 2 notes
                formatted_sections.append(f"- {note}")
        
        # Add business notes
        if 'business_notes' in pattern:
            formatted_sections.append("**Business Notes:**")
            for note in pattern['business_notes'][:2]:  # Max 2 notes
                formatted_sections.append(f"- {note}")
        
        formatted_sections.append("")  # Spacing between patterns
    
    return "\n".join(formatted_sections)
🔄 Phase 4 Integration Process
Step 1: Query Component Analysis
python# Analyze all query components to determine optimization needs
query_components = {
    'original_query': user_query,
    'query_type': query_type,
    'rules_context': rules_context,
    'discovery_context': discovery_context,
    'date_context': date_context
}

# Perform JOIN analysis
join_analyzer = JoinRequirementAnalyzer(business_rules_manager, schema_manager)
join_analysis = join_analyzer.analyze_join_requirements(query_components)

# Get relevant patterns
query_patterns = QueryPatterns()
patterns_context = query_patterns.get_relevant_patterns(query_components)
Step 2: Optimization Context Assembly
pythondef build_phase4_context(join_analysis: Dict, patterns_context: str) -> Dict:
    """Assemble Phase 4 optimization context"""
    
    return {
        'required_joins': join_analyzer.build_join_context(join_analysis),
        'query_patterns': patterns_context,
        'performance_guidance': _build_performance_guidance(join_analysis),
        'optimization_summary': _build_optimization_summary(join_analysis)
    }

def _build_performance_guidance(join_analysis: Dict) -> str:
    """Build performance guidance based on JOIN analysis"""
    
    guidance = ["\n## Performance Guidance:"]
    
    impact = join_analysis['performance_impact']
    if impact > 7:
        guidance.append("**High Performance Impact Query**")
        guidance.append("- Use specific WHERE clauses to limit result set")
        guidance.append("- Consider breaking into multiple simpler queries")
        guidance.append("- Ensure all JOIN columns are properly indexed")
    elif impact > 4:
        guidance.append("**Moderate Performance Impact Query**")
        guidance.append("- Apply filters early in WHERE clause")
        guidance.append("- Use LIMIT if appropriate for result set")
    else:
        guidance.append("**Low Performance Impact Query**")
        guidance.append("- Standard optimization practices apply")
    
    return "\n".join(guidance)
📊 Complete Phase 4 Example
Input: "Show officers with next vesting in Q4 by UK region"
Phase 4 Processing:
JOIN Analysis:
python# Required tables identified from previous phases:
# - participants.participant_detail (officers)
# - participants.participant_address (UK region)  
# - participants.participant_legal_detail (officer classification)
# - grants.grant_latest (vesting)
# - grants.tranches (vesting)
# - vesting_schedules.vesting_schedules (next vesting)
# - clients.client_latest (Q4 fiscal calendar)

join_analysis = {
    'required_tables': [
        'participants.participant_detail',
        'participants.participant_address',
        'participants.participant_legal_detail', 
        'grants.grant_latest',
        'grants.tranches',
        'vesting_schedules.vesting_schedules',
        'clients.client_latest'
    ],
    'optimal_join_path': [
        {'table': 'participants.participant_address', 'join_type': 'LEFT JOIN', 'join_condition': 'p.participant_hub_key = pa.participant_hub_key'},
        {'table': 'participants.participant_legal_detail', 'join_type': 'LEFT JOIN', 'join_condition': 'p.participant_hub_key = pl.participant_hub_key'},
        {'table': 'grants.grant_latest', 'join_type': 'LEFT JOIN', 'join_condition': 'p.participant_hub_key = g.participant_hub_key'},
        {'table': 'grants.tranches', 'join_type': 'LEFT JOIN', 'join_condition': 'g.grant_id = t.grant_id'},
        {'table': 'vesting_schedules.vesting_schedules', 'join_type': 'LEFT JOIN', 'join_condition': 't.tranche_id = vs.tranche_id'},
        {'table': 'clients.client_latest', 'join_type': 'LEFT JOIN', 'join_condition': 'pe.client_hub_key = c.client_hub_key'}
    ],
    'performance_impact': 6.5,
    'optimization_notes': [
        'High performance impact query - consider adding WHERE clauses early',
        'Vesting schedule JOIN detected - ensure date range filtering',
        'Multi-schema query (4 schemas) - network latency possible'
    ]
}
Pattern Matching:
python# Matches vesting + compliance + regional patterns
patterns_context = """
## Relevant Query Patterns:

**Pattern 1: Basic Vesting Schedule Lookup**
Use for: next vesting, upcoming vesting, vesting in period
Description: Find vesting events for participants in a date range
```sql
-- Pattern: Basic Vesting Lookup with Officer and Regional Filtering
SELECT 
    p.participant_name,
    p.employee_type,
    pa.country_code,
    pa.region_code,
    MIN(vs.vesting_date) as next_vesting_date,
    SUM(vs.vested_shares) as shares_vesting
FROM participants.participant_detail p
LEFT JOIN participants.participant_address pa ON p.participant_hub_key = pa.participant_hub_key
LEFT JOIN grants.grant_latest g ON p.participant_hub_key = g.participant_hub_key
LEFT JOIN grants.tranches t ON g.grant_id = t.grant_id
LEFT JOIN vesting_schedules.vesting_schedules vs ON t.tranche_id = vs.tranche_id
WHERE p.employee_type IN ('officer', 'executive', 'director')  -- Officer filter
  AND pa.country_code IN ('UK', 'United Kingdom', 'Britain')   -- Regional filter
  AND vs.vesting_date > CURRENT_DATE                           -- Next vesting
  AND vs.vesting_date BETWEEN '2024-01-01' AND '2024-03-31'    -- Q4 date range
GROUP BY p.participant_hub_key, p.participant_name, p.employee_type, pa.country_code, pa.region_code
ORDER BY next_vesting_date;
Performance Notes:

Index on (vesting_date, participant_hub_key) critical for performance
Use date range filters in WHERE clause before JOINs when possible
"""


### **Phase 4 Output**:
```python
# Complete Phase 4 context provided to GPT-4o
phase4_context = {
    'required_joins': """
    ## Required JOINs Analysis:
    
    **Required Tables:** participants.participant_detail, participants.participant_address, participants.participant_legal_detail, grants.grant_latest, grants.tranches, vesting_schedules.vesting_schedules, clients.client_latest
    
    **Recommended JOIN Path:**
```sql
    FROM participants.participant_detail p  -- Start with core table
    LEFT JOIN participants.participant_address pa
      ON p.participant_hub_key = pa.participant_hub_key
    LEFT JOIN participants.participant_legal_detail pl
      ON p.participant_hub_key = pl.participant_hub_key
    LEFT JOIN grants.grant_latest g
      ON p.participant_hub_key = g.participant_hub_key
    LEFT JOIN grants.tranches t
      ON g.grant_id = t.grant_id
    LEFT JOIN vesting_schedules.vesting_schedules vs
      ON t.tranche_id = vs.tranche_id
    LEFT JOIN clients.client_latest c
      ON pe.client_hub_key = c.client_hub_key
**Performance Impact:** 6.5/10

**Optimization Notes:**
- High performance impact query - consider adding WHERE clauses early
- Vesting schedule JOIN detected - ensure date range filtering
- Multi-schema query (4 schemas) - network latency possible
""",

'query_patterns': patterns_context,

'performance_guidance': """
## Performance Guidance:
**Moderate Performance Impact Query**
- Apply filters early in WHERE clause
- Use LIMIT if appropriate for result set
"""
}

### **GPT-4o Understanding** (thanks to Phase 4):
- ✅ **Knows exact JOIN path** - Optimal table order and conditions
- ✅ **Understands performance implications** - Will add early filtering
- ✅ **Has proven patterns** - Can adapt established query templates
- ✅ **Knows optimization techniques** - Will structure query efficiently
- ✅ **Understands business patterns** - Recognizes this as vesting+compliance+regional query type

## 🎯 **Phase 4 Success Criteria**

Phase 4 is successful when:

1. **JOIN Analysis Complete**:
```python
   assert len(join_analysis['required_tables']) > 0
   assert len(join_analysis['optimal_join_path']) > 0
   assert 'performance_impact' in join_analysis

Pattern Matching Accurate:

python   patterns = query_patterns.get_relevant_patterns(query_components)
   assert "Pattern" in patterns
   assert "sql" in patterns.lower()

Performance Guidance Generated:

python   guidance = build_performance_guidance(join_analysis)
   assert "Performance" in guidance
   assert len(join_analysis['optimization_notes']) > 0

Context Integration:

python   phase4_context = build_phase4_context(join_analysis, patterns)
   assert 'required_joins' in phase4_context
   assert 'query_patterns' in phase4_context
🚀 Phase 4 Deliverables
At the end of Phase 4, you have:

JoinRequirementAnalyzer class - Intelligent JOIN path optimization
QueryPatterns library - Comprehensive template collection for equity scenarios
Performance analysis - Automatic performance impact assessment
Pattern matching - Smart template selection based on query characteristics
Optimization guidance - Specific performance recommendations
JOIN path optimization - Minimum necessary JOINs with optimal order
Business pattern library - Proven SQL structures for equity use cases
Performance monitoring - Built-in performance impact scoring

Phase 4 ensures GPT-4o generates not just correct SQL, but optimized, maintainable, and performant SQL that follows established patterns and best practices for equity management systems!
