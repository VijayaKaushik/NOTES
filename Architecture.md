<img width="1920" height="1080" alt="Screenshot 2025-09-25 at 6 45 13 AM" src="https://github.com/user-attachments/assets/09877bcf-7efb-469a-8f20-3e8db3ee9d53" />

    subgraph "API Layer"
        API[FastAPI Routes<br/>📁 src/api/routes/]
        AUTH[Authentication<br/>📁 src/api/middleware/]
        SCHEMA[Request/Response Models<br/>📁 src/api/schemas/]
    end
    
    subgraph "Core Processing Engine"
        PROCESSOR[Query Processor<br/>📁 src/core/query_processor.py<br/>🔄 Main Orchestrator]
        SQLGEN[SQL Generator<br/>📁 src/core/sql_generator.py<br/>🤖 GPT-4o Integration]
        FORMATTER[Response Formatter<br/>📁 src/core/response_formatter.py]
    end
    
    subgraph "Discovery Services"
        ENTITY[Entity Discovery<br/>📁 src/discovery/entity_discovery.py<br/>🔍 DB Value Mapping]
        DATES[Date Processor<br/>📁 src/discovery/date_processor.py<br/>📅 Date Resolution]
        CACHE[Cache Manager<br/>📁 src/discovery/cache_manager.py<br/>⚡ Performance Layer]
    end
    
    subgraph "Business Rules Engine"
        RULES[Business Rules<br/>📁 src/rules/business_rules.py<br/>📋 Domain Logic]
        SCHEMA_CTX[Schema Context<br/>📁 src/rules/schema_context.py<br/>🏗️ DB Schema]
        PROMPTS[Prompt Templates<br/>📁 src/rules/prompts/<br/>💬 GPT Prompts]
    end
    
    subgraph "Data Layer"
        DB[Database Connection<br/>📁 src/database/connection.py<br/>🗄️ PostgreSQL]
        MODELS[Data Models<br/>📁 src/database/models.py<br/>📊 Pydantic Models]
    end
    
    subgraph "External Integrations"
        OPENAI[OpenAI Client<br/>📁 src/integrations/openai_client.py<br/>🧠 GPT-4o]
        REDIS[Cache Client<br/>📁 src/integrations/cache_client.py<br/>🚀 Redis]
    end
    
    subgraph "Configuration & Utils"
        CONFIG[Configuration<br/>📁 src/utils/config.py<br/>⚙️ Settings Management]
        LOGGER[Logging<br/>📁 src/utils/logger.py<br/>📝 Observability]
        MONITOR[Monitoring<br/>📁 src/monitoring/<br/>📈 Metrics & Tracing]
    end
    
    %% API Layer Connections
    API --> PROCESSOR
    AUTH --> API
    SCHEMA --> API
    
    %% Core Processing Flow
    PROCESSOR --> ENTITY
    PROCESSOR --> DATES
    PROCESSOR --> SQLGEN
    PROCESSOR --> FORMATTER
    
    %% Discovery Dependencies
    ENTITY --> DB
    ENTITY --> CACHE
    DATES --> DB
    DATES --> CACHE
    CACHE --> REDIS
    
    %% SQL Generation Dependencies
    SQLGEN --> RULES
    SQLGEN --> SCHEMA_CTX
    SQLGEN --> PROMPTS
    SQLGEN --> OPENAI
    
    %% Data Layer
    DB --> MODELS
    PROCESSOR --> DB
    
    %% Configuration
    CONFIG --> PROCESSOR
    CONFIG --> DB
    CONFIG --> OPENAI
    
    %% Monitoring
    LOGGER --> PROCESSOR
    LOGGER --> SQLGEN
    MONITOR --> API
    MONITOR --> PROCESSOR
    
    %% Sample Flow Annotations
    API -.->|1. User Query| PROCESSOR
    PROCESSOR -.->|2. Check Discovery Needs| ENTITY
    PROCESSOR -.->|3. Process Dates| DATES
    PROCESSOR -.->|4. Generate SQL| SQLGEN
    SQLGEN -.->|5. Apply Rules| RULES
    SQLGEN -.->|6. Call GPT-4o| OPENAI
    PROCESSOR -.->|7. Format Response| FORMATTER
    FORMATTER -.->|8. Return Result| API
    
    %% Styling
    classDef apiLayer fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    classDef coreEngine fill:#e8f5e8,stroke:#388e3c,stroke-width:3px
    classDef discovery fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef rules fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    classDef dataLayer fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    classDef external fill:#ffebee,stroke:#d32f2f,stroke-width:2px
    classDef config fill:#f0f4c3,stroke:#827717,stroke-width:2px
    
    class API,AUTH,SCHEMA apiLayer
    class PROCESSOR,SQLGEN,FORMATTER coreEngine
    class ENTITY,DATES,CACHE discovery
    class RULES,SCHEMA_CTX,PROMPTS rules
    class DB,MODELS dataLayer
    class OPENAI,REDIS external
    class CONFIG,LOGGER,MONITOR config
