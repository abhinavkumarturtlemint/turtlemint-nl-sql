# NL-SQL Query Processor — Architecture

```mermaid
flowchart TD
    User([Business User])
    UI[Streamlit Chat UI]

    subgraph Pipeline["FastAPI Backend - Agent Pipeline"]
        direction TB
        S1[1.Prompt Enhancer]
        S2[2.Intent Agent]
        S3[3.Table Agent + User Confirm]
        S4[4.Live Schema Fetch]
        S5[5.Column Prune Agent]
        S6[6.SQL Generator]
        S7{{7.Guardrails: SELECT only, LIMIT, timeout}}
        S8[8.Executor]
        S9[9.Result Formatter]
        S1 --> S2
        S2 --> S3
        S3 --> S4
        S4 --> S5
        S5 --> S6
        S6 --> S7
        S7 --> S8
        S8 --> S9
    end

    subgraph KB["Our Knowledge Base"]
        VI[(Vector Index - table names and summaries)]
        KF[(Knowledge File - Q to SQL examples, business defs)]
    end

    Claude{{Claude API - same model, different prompts}}

    subgraph TM["Turtlemint Source of Truth"]
        OM[(OpenMetadata - schema catalog)]
        CHE[clickhouse_query_run endpoint]
        CH[(ClickHouse - data warehouse)]
        CHE -->|read only SELECT| CH
    end

    Sync[Nightly Sync Job]
    Log[(Audit Log)]

    User -->|asks question| UI
    UI -->|POST /ask| S1
    S9 -->|answer and SQL| UI
    UI -->|shows answer| User
    S3 -.->|show tables, confirm| UI

    S2 -.->|semantic search| VI
    S6 -.->|fetch examples| KF

    S1 -.-> Claude
    S2 -.-> Claude
    S3 -.-> Claude
    S5 -.-> Claude
    S6 -.-> Claude
    S9 -.-> Claude

    S4 ==>|LIVE GET schema| OM
    S8 ==>|HTTP query| CHE

    Sync -->|pull tables| OM
    Sync -->|embed and store| VI

    S6 -.->|log| Log
    S8 -.->|log| Log

    classDef user fill:#fef3c7,stroke:#b45309,stroke-width:2px,color:#000
    classDef ui fill:#dbeafe,stroke:#1e40af,color:#000
    classDef pipe fill:#e0e7ff,stroke:#3730a3,color:#000
    classDef guard fill:#fef9c3,stroke:#a16207,stroke-width:2px,color:#000
    classDef kb fill:#dcfce7,stroke:#15803d,color:#000
    classDef llm fill:#fce7f3,stroke:#9d174d,color:#000
    classDef src fill:#fee2e2,stroke:#991b1b,color:#000
    classDef sync fill:#f3f4f6,stroke:#374151,color:#000

    class User user
    class UI ui
    class S1,S2,S3,S4,S5,S6,S8,S9 pipe
    class S7 guard
    class VI,KF kb
    class Claude llm
    class OM,CH,CHE src
    class Sync,Log sync
```

## Legend

| Element | Meaning |
|---|---|
| Yellow | Business user |
| Blue | Frontend (Streamlit) |
| Purple | Backend agent pipeline (FastAPI) |
| Bright yellow | Guardrails (safety layer) |
| Green | Our knowledge base (vector index + curated examples) |
| Pink | Claude API |
| Red | Turtlemint source of truth (OpenMetadata + ClickHouse) |
| Grey | Supporting infra (sync, audit log) |

| Arrow | Meaning |
|---|---|
| Solid arrow | Main pipeline flow (stage to stage) |
| Bold arrow | Live HTTP call to a Turtlemint system at runtime |
| Dotted arrow | Side call — to Claude, knowledge base, or audit log |
