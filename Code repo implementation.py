Key Files Implementation
1. Core Query Processor (src/core/query_processor.py)
pythonfrom typing import Dict, Optional
from .sql_generator import SQLGenerator
from ..discovery.entity_discovery import EntityDiscovery
from ..discovery.date_processor import DateProcessor
from ..utils.logger import get_logger

class QueryProcessor:
    """Main orchestrator for query processing"""
    
    def __init__(self):
        self.sql_generator = SQLGenerator()
        self.entity_discovery = EntityDiscovery()
        self.date_processor = DateProcessor() 
        self.logger = get_logger(__name__)
    
    async def process_query(self, user_query: str, context: Optional[Dict] = None) -> Dict:
        """Main entry point for query processing"""
        
        self.logger.info(f"Processing query: {user_query}")
        
        try:
            # 1. Determine processing strategy
            needs_discovery = self._needs_discovery(user_query)
            needs_date_processing = self._needs_date_processing(user_query)
            
            # 2. Run discovery if needed
            discovery_context = ""
            if needs_discovery:
                self.logger.info("Running entity discovery")
                discovery_context = await self.entity_discovery.discover_entities(user_query)
            
            # 3. Process dates if needed  
            date_context = ""
            if needs_date_processing:
                self.logger.info("Processing date expressions")
                date_context = await self.date_processor.process_dates(user_query)
            
            # 4. Generate SQL
            sql_result = await self.sql_generator.generate_sql(
                user_query=user_query,
                discovery_context=discovery_context,
                date_context=date_context,
                additional_context=context
            )
            
            return {
                "sql": sql_result.query,
                "explanation": sql_result.explanation,
                "discovery_used": bool(discovery_context),
                "date_processing_used": bool(date_context)
            }
            
        except Exception as e:
            self.logger.error(f"Error processing query: {e}")
            raise
    
    def _needs_discovery(self, query: str) -> bool:
        """Check if query needs entity discovery"""
        # Implementation from our earlier discussion
        pass
    
    def _needs_date_processing(self, query: str) -> bool:
        """Check if query needs date processing"""
        # Implementation from our earlier discussion
        pass
2. Business Rules Management (src/rules/business_rules.py)
pythonfrom typing import Dict
from .schema_context import SCHEMA_CONTEXT
from .date_rules import DATE_RULES

class BusinessRulesManager:
    """Centralized business rules management"""
    
    def __init__(self):
        self.rules = self._load_rules()
    
    def _load_rules(self) -> Dict:
        return {
            "vocabulary": self._load_vocabulary_rules(),
            "calculations": self._load_calculation_rules(),
            "compliance": self._load_compliance_rules(),
            "relationships": self._load_relationship_rules()
        }
    
    def get_rules_context(self, query_type: str = "general") -> str:
        """Get relevant rules for query type"""
        
        base_context = SCHEMA_CONTEXT + "\n"
        
        # Add relevant rule sections
        for rule_type, rules in self.rules.items():
            if self._is_rule_relevant(query_type, rule_type):
                base_context += f"\n{rules}\n"
        
        return base_context
    
    def _load_vocabulary_rules(self) -> str:
        return """
        Business Term Mappings:
        - "Officers" = participant_detail.employee_type IN ('officer', 'executive', 'director')
        - "Active participants" = participant_detail.status = 'active' AND termination_date IS NULL
        - "Vested grants" = vesting_date <= CURRENT_DATE
        """
    
    # Additional rule loading methods...
3. Configuration Management (src/utils/config.py)
pythonfrom typing import Any, Dict
from pydantic_settings import BaseSettings
from functools import lru_cache
import yaml
import os

class Settings(BaseSettings):
    """Application settings"""
    
    # Database
    database_url: str
    database_pool_size: int = 10
    
    # OpenAI
    openai_api_key: str
    openai_model: str = "gpt-4o"
    openai_max_tokens: int = 4000
    
    # Cache
    redis_url: str = "redis://localhost:6379"
    cache_ttl_seconds: int = 3600
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Environment
    environment: str = "development"
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    return Settings()

def load_config_file(environment: str = None) -> Dict[str, Any]:
    """Load environment-specific configuration"""
    
    env = environment or get_settings().environment
    config_path = f"config/{env}.yaml"
    
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    return {}
4. API Layer (src/api/routes/query.py)
pythonfrom fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict

from ...core.query_processor import QueryProcessor
from ...utils.logger import get_logger
from ..schemas.query_schemas import QueryRequest, QueryResponse

router = APIRouter(prefix="/api/v1", tags=["queries"])
logger = get_logger(__name__)

class QueryProcessor:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = QueryProcessor()
        return cls._instance

@router.post("/query", response_model=QueryResponse)
async def execute_query(
    request: QueryRequest,
    processor: QueryProcessor = Depends(QueryProcessor.get_instance)
):
    """Execute natural language query and return SQL + results"""
    
    try:
        result = await processor.process_query(
            user_query=request.query,
            context=request.context
        )
        
        return QueryResponse(
            sql=result["sql"],
            explanation=result["explanation"],
            discovery_used=result["discovery_used"],
            date_processing_used=result["date_processing_used"]
        )
        
    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "equity-query-engine"}
5. Testing Structure (tests/unit/test_sql_generator.py)
pythonimport pytest
from unittest.mock import Mock, patch
from src.equity_query_engine.core.sql_generator import SQLGenerator

class TestSQLGenerator:
    
    @pytest.fixture
    def sql_generator(self):
        return SQLGenerator()
    
    @pytest.fixture
    def mock_openai_response(self):
        return Mock(
            choices=[Mock(message=Mock(content="SELECT * FROM participants.participant_detail;"))]
        )
    
    @patch('openai.ChatCompletion.create')
    def test_simple_query_generation(self, mock_openai, sql_generator, mock_openai_response):
        """Test basic SQL generation"""
        
        mock_openai.return_value = mock_openai_response
        
        result = sql_generator.generate_sql("Show all participants")
        
        assert "SELECT" in result.query
        assert "participants.participant_detail" in result.query
        mock_openai.assert_called_once()
    
    def test_date_context_integration(self, sql_generator):
        """Test SQL generation with date context"""
        
        date_context = "Date: 'next month' → DATE_TRUNC('month', CURRENT_DATE + INTERVAL '1 month')"
        
        with patch.object(sql_generator, '_call_openai') as mock_call:
            mock_call.return_value = "SELECT * FROM grants WHERE vesting_date >= DATE_TRUNC('month', CURRENT_DATE + INTERVAL '1 month');"
            
            result = sql_generator.generate_sql(
                user_query="Show vesting next month",
                date_context=date_context
            )
            
            assert "DATE_TRUNC" in result.query
Benefits of This Structure:
✅ Separation of Concerns: Each component has a clear responsibility
✅ Testability: Easy to unit test individual components
✅ Configurability: Environment-specific settings
✅ Scalability: Can add new features without major refactoring
✅ Maintainability: Clear where to make changes
✅ Documentation: Self-documenting structure
