graph TB
    %% User Interface Layer
    subgraph UI["User Interface Layer"]
        Chat["Chat Interface<br/>(Next.js)"]
        Dashboard["Dashboard<br/>(Analytics)"]
        AdminPanel["Admin Panel<br/>(Approvals)"]
    end

    %% API Gateway
    API["API Gateway<br/>(FastAPI + WebSocket)"]

    %% Orchestrator Agent
    subgraph Orchestrator["Orchestrator Agent (LangGraph Core)"]
        IntentAnalyzer["Intent Analyzer"]
        WorkflowPlanner["Workflow Planner"]
        RiskAssessor["Risk Assessor"]
        AgentCoordinator["Agent Coordinator"]
        ResponseFormatter["Response Formatter"]
    end

    %% Specialist Agents
    subgraph Agents["Specialist Agents"]
        SchemaAgent["Schema Context Agent"]
        QueryAgent["Query Builder Agent"]
        ImpactAgent["Impact Analysis Agent"]
        ApprovalAgent["Approval Management Agent"]
        ExecutionAgent["Execution Management Agent"]
        MemoryAgent["Memory Context Agent"]
    end

    %% MCP Servers
    subgraph MCP["MCP Servers"]
        DatabaseMCP["Database Operations MCP"]
        ImpactMCP["Impact Analysis MCP"]
        ApprovalMCP["Approval Workflow MCP"]
        ExecutionMCP["Execution Monitor MCP"]
    end

    %% Infrastructure Layer
    subgraph Infrastructure["Infrastructure Layer"]
        PostgreSQL["PostgreSQL<br/>(Primary + Target DB)"]
        Redis["Redis<br/>(Cache + Sessions)"]
        Vector["pgvector<br/>(Embeddings)"]
        MessageQueue["Message Queue<br/>(Celery)"]
    end

    %% External Services
    subgraph External["External Services"]
        GroqAPI["Groq API<br/>(LLM Models)"]
        Notifications["Notifications<br/>(Slack, Email)"]
        Monitoring["Monitoring<br/>(Metrics & Logs)"]
    end

    %% Connections
    UI --> API
    API --> Orchestrator
    
    Orchestrator --> Agents
    Agents --> MCP
    MCP --> Infrastructure
    MCP --> External
    
    %% Specific connections
    SchemaAgent --> DatabaseMCP
    QueryAgent --> DatabaseMCP
    ImpactAgent --> ImpactMCP
    ApprovalAgent --> ApprovalMCP
    ExecutionAgent --> ExecutionMCP
    MemoryAgent --> Redis
    MemoryAgent --> Vector
    
    %% External connections
    DatabaseMCP --> PostgreSQL
    ApprovalMCP --> Notifications
    ExecutionMCP --> Monitoring
    QueryAgent --> GroqAPI
    IntentAnalyzer --> GroqAPI

    %% Styling
    classDef uiClass fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef agentClass fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef mcpClass fill:#e8f5e8,stroke:#1b5e20,stroke-width:2px
    classDef infraClass fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef externalClass fill:#fce4ec,stroke:#880e4f,stroke-width:2px

    class Chat,Dashboard,AdminPanel uiClass
    class IntentAnalyzer,WorkflowPlanner,RiskAssessor,AgentCoordinator,ResponseFormatter,SchemaAgent,QueryAgent,ImpactAgent,ApprovalAgent,ExecutionAgent,MemoryAgent agentClass
    class DatabaseMCP,ImpactMCP,ApprovalMCP,ExecutionMCP mcpClass
    class PostgreSQL,Redis,Vector,MessageQueue infraClass
    class GroqAPI,Notifications,Monitoring externalClass

---

## 🔄 Agent Interaction Flow

sequenceDiagram
    participant User as 👤 User
    participant API as 🌐 API Gateway
    participant Orch as 🧠 Orchestrator
    participant Schema as 🗃️ Schema Agent
    participant Query as ⚡ Query Agent
    participant Impact as 📈 Impact Agent
    participant Approval as ✅ Approval Agent
    participant Exec as 🚀 Execution Agent
    participant DB as 🐘 PostgreSQL

    User->>API: "Update product prices by 10%"
    API->>Orch: Process natural language query
    
    Note over Orch: Intent Analysis & Risk Assessment
    Orch->>Orch: Classify: UPDATE, HIGH Risk
    Orch->>Orch: Plan: Schema→Query→Impact→Approval→Exec
    
    par Schema Discovery
        Orch->>Schema: Get schema context
        Schema->>DB: INSPECT schema, tables, relationships
        DB-->>Schema: Schema metadata + relationships
        Schema-->>Orch: Relevant tables: products, categories
    and Memory Context
        Orch->>Schema: Load user context & preferences
        Note over Schema: Cache hit: schema loaded
    end
    
    Orch->>Query: Generate SQL from intent + schema
    Query->>Query: Build: UPDATE products SET price = price * 1.1
    Query->>Query: Validate syntax & optimize
    Query-->>Orch: Optimized SQL + alternatives
    
    Orch->>Impact: Analyze UPDATE impact
    Impact->>DB: Estimate affected rows
    Impact->>DB: Check foreign key cascades
    DB-->>Impact: ~2,500 rows, no cascades
    Impact-->>Orch: Risk: HIGH, 2.5K rows, backup needed
    
    Note over Orch: Risk = HIGH → Approval Required
    Orch->>Approval: Create approval request
    Approval->>Approval: Route to manager (risk level)
    Approval->>API: Notify via Slack/Email
    
    Note over User: Manager receives notification
    User->>API: Manager approves via dashboard
    API->>Approval: Approval granted
    Approval-->>Orch: ✅ APPROVED by manager
    
    Orch->>Exec: Execute with approved SQL
    Exec->>DB: CREATE backup snapshot
    Exec->>DB: BEGIN TRANSACTION
    Exec->>DB: UPDATE products SET price = price * 1.1...
    DB-->>Exec: 2,487 rows updated
    Exec->>DB: COMMIT TRANSACTION
    Exec-->>Orch: ✅ Success: 2,487 rows updated
    
    Orch->>API: Format success response
    API-->>User: ✅ Update completed: 2,487 products updated

---

## 📊 Data Flow Architecture

flowchart TD
    A[👤 User Input] --> B{🔍 Intent Classification}
    
    B -->|SELECT| C[📊 Simple Flow]
    B -->|UPDATE/DELETE| D[⚠️ Complex Flow]
    B -->|INSERT| E[📝 Moderate Flow]
    
    C --> F[🗃️ Schema Context]
    D --> F
    E --> F
    
    F --> G[⚡ Query Generation]
    
    G --> H{🎯 Query Type Check}
    H -->|READ| I[🚀 Direct Execution]
    H -->|WRITE| J[📈 Impact Analysis]
    
    J --> K{⚠️ Risk Level}
    K -->|LOW| L[📝 Auto Approve]
    K -->|MEDIUM| M[👥 Team Approval]
    K -->|HIGH| N[👔 Manager Approval]
    K -->|CRITICAL| O[🏢 Executive Approval]
    
    L --> P[🚀 Safe Execution]
    M --> Q{✅ Approved?}
    N --> Q
    O --> Q
    
    Q -->|Yes| P
    Q -->|No| R[❌ Denied]
    
    I --> S[📋 Results Processing]
    P --> T[🔍 Integrity Check]
    T --> S
    
    S --> U[📊 Visualization]
    U --> V[👤 User Response]
    
    R --> W[💡 Alternatives]
    W --> V

    %% Styling
    classDef startEnd fill:#e8f5e8,stroke:#2e7d32,stroke-width:3px
    classDef process fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    classDef decision fill:#fff3e0,stroke:#ef6c00,stroke-width:2px
    classDef approval fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    classDef execution fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    
    class A,V startEnd
    class F,G,S,U process
    class B,H,K,Q decision
    class L,M,N,O approval
    class I,J,P,T execution

---

## 🔧 MCP Server Tool Architecture

graph LR
    subgraph "🗄️ Database Operations MCP"
        DB1[inspect_schema]
        DB2[validate_query_syntax]
        DB3[generate_query_from_intent]
        DB4[execute_read_query]
        DB5[get_sample_data]
    end
    
    subgraph "📊 Impact Analysis MCP"
        IA1[analyze_update_impact]
        IA2[analyze_delete_impact]
        IA3[estimate_affected_rows]
        IA4[check_referential_integrity]
        IA5[generate_rollback_plan]
    end
    
    subgraph "📋 Approval Workflow MCP"
        AW1[create_approval_request]
        AW2[check_approval_status]
        AW3[notify_approvers]
        AW4[escalate_approval]
        AW5[audit_approval_decision]
    end
    
    subgraph "⚡ Execution Monitor MCP"
        EM1[execute_with_transaction]
        EM2[monitor_execution_progress]
        EM3[create_pre_execution_backup]
        EM4[execute_rollback]
        EM5[verify_execution_integrity]
    end
    
    %% Agent connections to tools
    Schema[🗃️ Schema Agent] --> DB1
    Schema --> DB5
    
    Query[⚡ Query Agent] --> DB2
    Query --> DB3
    Query --> DB4
    
    Impact[📈 Impact Agent] --> IA1
    Impact --> IA2
    Impact --> IA3
    Impact --> IA4
    Impact --> IA5
    
    Approval[✅ Approval Agent] --> AW1
    Approval --> AW2
    Approval --> AW3
    Approval --> AW4
    Approval --> AW5
    
    Execution[🚀 Execution Agent] --> EM1
    Execution --> EM2
    Execution --> EM3
    Execution --> EM4
    Execution --> EM5

---

## 🚨 Error Handling & Recovery Flow

flowchart TB
    Start[🚀 Operation Start] --> Monitor[📊 Continuous Monitoring]
    
    Monitor --> Check{🔍 Error Detected?}
    Check -->|No| Continue[✅ Continue Operation]
    Check -->|Yes| Classify[🏷️ Classify Error Type]
    
    Classify --> Syntax{📝 Syntax Error?}
    Classify --> Permission{🔒 Permission Error?}
    Classify --> Integrity{🔗 Integrity Error?}
    Classify --> Performance{⚡ Performance Error?}
    Classify --> System{🖥️ System Error?}
    
    Syntax --> FixSQL[🔧 Auto-fix SQL]
    Permission --> RequestAccess[📞 Request Access]
    Integrity --> Rollback1[↩️ Transaction Rollback]
    Performance --> Optimize[⚡ Query Optimization]
    System --> Retry[🔄 Retry with Backoff]
    
    FixSQL --> Validate{✅ Valid Fix?}
    Validate -->|Yes| Continue
    Validate -->|No| UserHelp[👤 Request User Help]
    
    RequestAccess --> UserHelp
    
    Rollback1 --> CheckData{🔍 Data Consistent?}
    CheckData -->|Yes| UserHelp
    CheckData -->|No| RestoreBackup[💾 Restore from Backup]
    
    Optimize --> ReExecute[🔄 Re-execute Optimized]
    ReExecute --> Continue
    
    Retry --> RetryCount{🔢 Max Retries?}
    RetryCount -->|No| Monitor
    RetryCount -->|Yes| Escalate[🚨 Escalate to Admin]
    
    RestoreBackup --> Verify[✅ Verify Restoration]
    Verify --> UserHelp
    
    UserHelp --> UserDecision{👤 User Decision}
    UserDecision -->|Retry| Start
    UserDecision -->|Modify| ModifyQuery[📝 Modify Query]
    UserDecision -->|Cancel| Cancel[❌ Cancel Operation]
    
    ModifyQuery --> Start
    Escalate --> AdminAction[👔 Admin Intervention]
    Continue --> Success[🎉 Operation Complete]
    
    %% Styling
    classDef startEnd fill:#e8f5e8,stroke:#2e7d32,stroke-width:3px
    classDef error fill:#ffebee,stroke:#d32f2f,stroke-width:2px
    classDef recovery fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    classDef decision fill:#fff3e0,stroke:#ef6c00,stroke-width:2px
    
    class Start,Success startEnd
    class Classify,Syntax,Permission,Integrity,Performance,System error
    class FixSQL,Rollback1,Optimize,Retry,RestoreBackup,ModifyQuery recovery
    class Check,Validate,CheckData,RetryCount,UserDecision decision