# Architecture Document: Drone Security Analyst Agent

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    DRONE SECURITY ANALYST AGENT                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐                           │
│  │  Telemetry    │    │  Frame       │                           │
│  │  Simulator    │    │  Simulator   │                           │
│  │  (telemetry.py│    │  (frames.py) │                           │
│  └──────┬───────┘    └──────┬───────┘                           │
│         │                    │                                   │
│         └────────┬───────────┘                                   │
│                  ▼                                                │
│  ┌──────────────────────────┐                                   │
│  │  VLM Frame Analyzer      │  ◄── Google Gemini 2.0 Flash     │
│  │  (vlm_analyzer.py)       │                                   │
│  └──────────┬───────────────┘                                   │
│             ▼                                                    │
│  ┌──────────────────────────┐                                   │
│  │  LangChain Agent         │  ◄── ConversationBufferMemory    │
│  │  (security_agent.py)     │                                   │
│  │  ┌────────────────────┐  │                                   │
│  │  │ Tools:             │  │                                   │
│  │  │ • log_event        │  │                                   │
│  │  │ • check_alert_rules│  │                                   │
│  │  │ • query_past_events│  │                                   │
│  │  │ • generate_summary │  │                                   │
│  │  └────────────────────┘  │                                   │
│  └──────┬──────────┬────────┘                                   │
│         │          │                                             │
│    ┌────▼────┐ ┌───▼──────────┐  ┌──────────────┐              │
│    │ SQLite  │ │ ChromaDB     │  │ Alert Rules  │              │
│    │ Store   │ │ Store        │  │ Engine       │              │
│    │(struct) │ │ (semantic)   │  │(rules_engine)│              │
│    └─────────┘ └──────────────┘  └──────────────┘              │
│                                                                  │
│    ┌──────────────────────────┐                                  │
│    │  Query CLI (query.py)    │                                  │
│    └──────────────────────────┘                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Simulators
- **Telemetry Simulator**: Generates GPS, altitude, battery, wind data per frame
- **Frame Simulator**: 30 diverse text descriptions covering 24hr patrol cycle

### 2. VLM Frame Analyzer
- Uses Google Gemini 2.0 Flash for frame analysis
- Security-focused system prompt extracts objects, event types, risk levels
- Structured JSON output with fallback parsing

### 3. LangChain Agent
- AgentExecutor with tool-calling capability
- ConversationBufferMemory for cross-frame pattern recognition
- 4 custom tools for logging, alerts, queries, and summaries

### 4. Dual Indexing (Cross-Domain Innovation)
- **SQLite**: Structured queries by object, time, location
- **ChromaDB**: Semantic vector search for natural language queries
- Both populated simultaneously for comprehensive coverage

### 5. Alert Rules Engine
- 8 configurable rules with severity levels
- Evaluates each frame against all rules
- Tracks alert history to inform agent decisions

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| LLM | Gemini 2.0 Flash | Fast, cost-effective, good JSON output |
| Agent Framework | LangChain | Industry standard, tool-calling support |
| Structured DB | SQLite | Built-in Python support, zero setup |
| Vector DB | ChromaDB | Easy setup, built-in embeddings |
| Console UX | Rich library | Professional colored output for demos |
| Memory | ConversationBuffer | Full context for pattern recognition |
