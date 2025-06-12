graph TD
    A[User Interface] --> B[API Gateway]
    B --> C[Orchestrator Agent]
    
    C --> D[Schema Agent]
    C --> E[Query Agent]
    C --> F[Impact Agent]
    C --> G[Approval Agent]
    C --> H[Execution Agent]
    C --> I[Memory Agent]
    
    D --> J[Database MCP]
    E --> J
    F --> K[Impact MCP]
    G --> L[Approval MCP]
    H --> M[Execution MCP]
    I --> N[Redis Cache]
    
    J --> O[PostgreSQL]
    K --> O
    L --> P[Notifications]
    M --> O
    M --> Q[Monitoring]
    
    E --> R[Groq API]