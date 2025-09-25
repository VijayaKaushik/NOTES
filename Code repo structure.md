equity-query-engine/
├── README.md
├── requirements.txt
├── pyproject.toml
├── .env.example
├── docker-compose.yml
├── 
├── src/
│   └── equity_query_engine/
│       ├── __init__.py
│       ├── main.py                    # FastAPI app entry point
│       │
│       ├── core/                      # Core business logic
│       │   ├── __init__.py
│       │   ├── query_processor.py     # Main orchestrator
│       │   ├── sql_generator.py       # GPT-4o SQL generation
│       │   └── response_formatter.py  # Format results
│       │
│       ├── discovery/                 # Data discovery system
│       │   ├── __init__.py
│       │   ├── entity_discovery.py    # Find DB variations
│       │   ├── date_processor.py      # Date resolution
│       │   └── cache_manager.py       # Discovery caching
│       │
│       ├── rules/                     # Business rules & prompts
│       │   ├── __init__.py
│       │   ├── schema_context.py      # DB schema definitions
│       │   ├── business_rules.py      # Equity domain rules
│       │   ├── date_rules.py          # Date handling rules
│       │   └── prompts/               # GPT prompt templates
│       │       ├── __init__.py
│       │       ├── base_prompts.py
│       │       ├── discovery_prompts.py
│       │       └── sql_generation_prompts.py
│       │
│       ├── database/                  # Data layer
│       │   ├── __init__.py
│       │   ├── connection.py          # DB connection management
│       │   ├── models.py              # Pydantic models
│       │   └── migrations/            # Schema migrations
│       │
│       ├── integrations/              # External services
│       │   ├── __init__.py
│       │   ├── openai_client.py       # GPT-4o client
│       │   └── cache_client.py        # Redis/memory cache
│       │
│       ├── api/                       # API layer
│       │   ├── __init__.py
│       │   ├── routes/
│       │   │   ├── __init__.py
│       │   │   ├── query.py           # Main query endpoints
│       │   │   └── health.py          # Health check
│       │   ├── middleware/
│       │   │   ├── __init__.py
│       │   │   ├── auth.py            # Authentication
│       │   │   └── logging.py         # Request logging
│       │   └── schemas/               # API request/response models
│       │       ├── __init__.py
│       │       └── query_schemas.py
│       │
│       ├── utils/                     # Utilities
│       │   ├── __init__.py
│       │   ├── logger.py              # Logging setup
│       │   ├── config.py              # Configuration management
│       │   └── exceptions.py          # Custom exceptions
│       │
│       └── monitoring/                # Observability
│           ├── __init__.py
│           ├── metrics.py             # Performance metrics
│           └── tracing.py             # Request tracing
│
├── tests/                            # Test suite
│   ├── __init__.py
│   ├── conftest.py                   # Pytest fixtures
│   ├── unit/                         # Unit tests
│   │   ├── test_sql_generator.py
│   │   ├── test_date_processor.py
│   │   └── test_discovery.py
│   ├── integration/                  # Integration tests
│   │   ├── test_query_flow.py
│   │   └── test_database.py
│   └── fixtures/                     # Test data
│       ├── sample_queries.py
│       └── mock_responses.py
│
├── config/                           # Configuration files
│   ├── development.yaml
│   ├── production.yaml
│   └── schema_mappings.yaml          # Entity mappings
│
├── scripts/                          # Utility scripts
│   ├── setup_db.py                   # Database setup
│   ├── migrate.py                    # Run migrations
│   └── load_test_data.py             # Test data loader
│
└── docs/                             # Documentation
    ├── API.md
    ├── DEPLOYMENT.md
    ├── BUSINESS_RULES.md
    └── examples/
        └── sample_queries.md
