# 🛡️ Drone Security Analyst Agent

An AI-powered autonomous drone surveillance system that monitors industrial properties 24/7, detects security threats in real-time, and generates searchable event history using **LangChain**, **OpenAI GPT-4o-mini**, **Grounding DINO + DeepSORT**, and dual-database indexing (**SQLite + ChromaDB Cloud**).

> **Property:** SecureTech Industrial Complex · **Drone:** DRN-01 · **Mode:** Autonomous Patrol

---

## 📑 Table of Contents

- [Architecture Overview](#-architecture-overview)
- [How It Works — Complete Flow](#-how-it-works--complete-flow)
  - [1. Simulated Patrol Pipeline](#1-simulated-patrol-pipeline-mainpy)
  - [2. Video Upload Analysis Pipeline](#2-video-upload-analysis-pipeline-serverpy)
  - [3. Query & Retrieval Pipeline](#3-query--retrieval-pipeline)
- [Module Breakdown](#-module-breakdown)
- [Alert Rules Engine](#-alert-rules-engine)
- [Agent Tools](#-agent-tools)
- [Dual Database Architecture](#-dual-database-architecture)
- [Web Dashboard (Aegis Drone Command)](#-web-dashboard--aegis-drone-command)
- [API Reference](#-api-reference)
- [Quick Start](#-quick-start)
- [Project Structure](#-project-structure)
- [Design Decisions](#-design-decisions)
- [Testing](#-testing)
- [Future Improvements](#-future-improvements)

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                     AEGIS DRONE COMMAND CENTER                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────┐    │
│  │  Simulated   │   │  Real Video  │   │   Telemetry          │    │
│  │  30 Frames   │   │  Upload      │   │   Simulator          │    │
│  │  (24hr cycle)│   │  (MP4/AVI)   │   │   (GPS/Battery/Alt)  │    │
│  └──────┬───────┘   └──────┬───────┘   └──────────┬───────────┘    │
│         │                  │                       │                │
│         │          ┌───────┴────────┐              │                │
│         │          │  Grounding     │              │                │
│         │          │  DINO +        │              │                │
│         │          │  DeepSORT      │              │                │
│         │          └───────┬────────┘              │                │
│         │                  │                       │                │
│         ▼                  ▼                       │                │
│  ┌─────────────────────────────────────┐           │                │
│  │     VLM Analyzer (GPT-4o-mini)      │◄──────────┘                │
│  │  Structured JSON: objects, risk,    │                            │
│  │  event_type, is_suspicious, action  │                            │
│  └──────────────┬──────────────────────┘                            │
│                 │                                                    │
│                 ▼                                                    │
│  ┌─────────────────────────────────────┐                            │
│  │  LangChain ReAct Agent (LangGraph)  │                            │
│  │  ┌─────────┐ ┌──────────┐          │                            │
│  │  │log_event│ │check_    │          │                            │
│  │  │         │ │alert_    │          │                            │
│  │  │         │ │rules     │          │                            │
│  │  └────┬────┘ └────┬─────┘          │                            │
│  │  ┌────┴────┐ ┌────┴─────┐          │                            │
│  │  │query_   │ │generate_ │          │                            │
│  │  │past_    │ │summary   │          │                            │
│  │  │events   │ │          │          │                            │
│  │  └─────────┘ └──────────┘          │                            │
│  └──────────────┬──────────────────────┘                            │
│                 │                                                    │
│        ┌────────┴────────┐                                          │
│        ▼                 ▼                                          │
│  ┌───────────┐    ┌────────────┐    ┌──────────────┐               │
│  │  SQLite   │    │  ChromaDB  │    │ Alert Engine │               │
│  │ Structured│    │  Semantic  │    │  8 Rules     │               │
│  │  Queries  │    │  Vector    │    │  4 Severity  │               │
│  │           │    │  Search    │    │  Levels      │               │
│  └───────────┘    └────────────┘    └──────────────┘               │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│  OUTPUT INTERFACES                                                  │
│  ┌────────────┐  ┌────────────┐  ┌───────────┐  ┌──────────────┐  │
│  │ Web UI     │  │ Streamlit  │  │ Rich CLI  │  │ Query CLI    │  │
│  │ (FastAPI)  │  │ Dashboard  │  │ (main.py) │  │ (query.py)   │  │
│  └────────────┘  └────────────┘  └───────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 How It Works — Complete Flow

### 1. Simulated Patrol Pipeline (`main.py`)

This is the core monitoring pipeline that processes 30 pre-defined frames covering a full 24-hour patrol cycle.

```mermaid
flowchart TD
    A["🚀 Start: python main.py"] --> B["Initialize Components"]
    B --> B1["SQLiteStore — Create/clear DB"]
    B --> B2["ChromaStore — Create/clear collection"]
    B --> B3["AlertManager — Reset rules"]
    B --> B4["TelemetrySimulator — Reset battery"]

    B1 & B2 & B3 & B4 --> C["Initialize SecurityAgent\n(LangGraph ReAct Agent + 4 Tools)"]

    C --> D["Load 30 Simulated Frames\n(06:00 → 01:00 next day)"]

    D --> E{{"FOR EACH FRAME (i = 1..30)"}}

    E --> F["Step 1: Generate Telemetry\n• GPS coordinates\n• Altitude (8-25m by location)\n• Battery drain (1-3% per frame)\n• Wind speed simulation"]

    F --> G["Step 2: VLM Analysis\n(GPT-4o-mini API Call)\n• Send frame description + telemetry\n• Receive structured JSON:\n  objects, event_type, risk_level,\n  is_suspicious, recommended_action"]

    G --> H["Step 3: Agent Processing\n(LangGraph ReAct Agent)\n• Receives frame + analysis + telemetry\n• Decides which tools to call\n• Maintains conversation memory\n  (last 10 exchanges)"]

    H --> H1["Tool: log_event\n→ Write to SQLite\n→ Write to ChromaDB\n→ Track vehicle re-entries"]
    H --> H2["Tool: check_alert_rules\n→ Evaluate 8 alert rules\n→ Fire alerts to DB"]
    H --> H3["Tool: query_past_events\n→ Cross-reference with\n  previous frames\n→ Pattern detection"]

    H1 & H2 & H3 --> I["Step 4: Print Results\n• Rich console output\n• Color-coded risk levels\n• Alert notifications"]

    I --> J{"More frames?"}
    J -- "Yes (4s delay)" --> E
    J -- "No" --> K["Generate AI Summary\n(Agent + generate_summary tool)"]

    K --> L["Print Session Report\n• Statistics table\n• Alert log\n• Suspicious activity summary"]

    L --> M["✅ Session Complete\nData saved to SQLite + ChromaDB"]

    style A fill:#00c853,color:#000
    style G fill:#1565c0,color:#fff
    style H fill:#6a1b9a,color:#fff
    style M fill:#00c853,color:#000
```

**What happens at each step:**

| Step | Component | Input | Output |
|------|-----------|-------|--------|
| 1 | `TelemetrySimulator` | Time + Location | GPS, altitude, battery, wind, status |
| 2 | `vlm_analyzer.analyze_frame()` | Text description + telemetry | Structured JSON (objects, risk, event_type) |
| 3 | `SecurityAgent.process_frame()` | Frame + analysis + telemetry | Agent response, alerts, tool call results |
| 4 | `Rich Console` | All above | Color-coded terminal output |

---

### 2. Video Upload Analysis Pipeline (`server.py`)

When a user uploads a real video through the web dashboard, it goes through a **dual-detection pipeline** combining Grounding DINO (open-vocabulary detection with text prompts) with GPT-4o-mini Vision (contextual understanding).

```mermaid
flowchart TD
    A["📹 User Uploads Video\n(MP4/AVI/MKV)"] --> B["Save to data/ directory"]

    B --> C["Extract Frames\n• Interval: 2 sec (dynamic)\n• Max: 20 frames\n• JPEG quality: 90%\n• Keep raw + base64"]

    C --> D{{"FOR EACH FRAME"}}

    D --> E["🔍 Step 1: Grounding DINO\n(Open-Vocab + DeepSORT)"]
    E --> E1["Detect objects via\ntext prompts — 28+\nsecurity-relevant classes"]
    E1 --> E2["Track objects across frames\nwith persistent IDs"]
    E2 --> E3["Output: objects list +\ndetections with confidence %"]

    D --> F["🧠 Step 2: Vision AI\n(GPT-4o-mini Vision API)"]
    E3 --> F
    F --> F1["Send base64 frame image\nat HIGH detail resolution"]
    F1 --> F2["Enhanced prompt asks for:\n• ALL people (count + clothing)\n• ALL vehicles (type + color)\n• ALL animals + objects\n• Activities + concerns"]
    F2 --> F3["Grounding DINO results sent\nas hints for cross-referencing"]
    F3 --> F4["Output: 4-6 sentence\ndetailed description"]

    F4 --> G["🔬 Step 3: Security Analysis\n(GPT-4o-mini Text API)"]
    G --> G1["Analyze description against\nsecurity rules and context"]
    G1 --> G2["Output: Structured JSON\n(objects, event_type, risk,\nis_suspicious, action)"]

    G2 --> H["🔀 Step 4: Merge Results"]
    E3 --> H
    H --> H1["Combine G-DINO objects\n+ VLM objects\n(deduplicated)"]
    H1 --> H2["Add detection counts\n+ confidence scores"]

    H2 --> I["📡 Stream via SSE\n(Server-Sent Events)"]
    I --> J["Web Dashboard displays:\n• Objects detected\n• G-DINO confidence %\n• Risk assessment\n• Recommended action"]

    J --> K{"More frames?"}
    K -- "Yes" --> D
    K -- "No" --> L["✅ Analysis Complete"]

    style A fill:#ff6d00,color:#000
    style E fill:#00c853,color:#000
    style F fill:#1565c0,color:#fff
    style G fill:#6a1b9a,color:#fff
    style H fill:#ffd600,color:#000
    style L fill:#00c853,color:#000
```

**Why dual detection?**

| Detection Method | Strengths | Weaknesses |
|------------------|-----------|------------|
| **Grounding DINO** | Open-vocabulary (detect anything via text), bounding boxes, confidence scores, zero-shot — no retraining needed | Heavier than YOLO (~2-4s/frame on CPU), requires HuggingFace model download |
| **GPT-4o-mini Vision** | Understands context, describes activities, identifies suspicious behavior | Can miss small objects, no bounding boxes, slower |
| **Combined** | ✅ Best of both — open-vocabulary detection AND contextual understanding | Slightly more API cost |

---

### 3. Query & Retrieval Pipeline

After a monitoring session, all data is queryable through multiple interfaces.

```mermaid
flowchart LR
    subgraph Input["User Query"]
        Q1["python query.py\n--object 'truck'"]
        Q2["python query.py\n--search 'suspicious\nnighttime activity'"]
        Q3["python query.py\n--alerts"]
        Q4["Web Dashboard\nQuery Panel"]
    end

    subgraph Search["Search Engines"]
        S1["SQLite\nKeyword Search\n(LIKE queries)"]
        S2["ChromaDB\nSemantic Search\n(Vector similarity)"]
    end

    subgraph Output["Results"]
        R1["Structured Table\n(Frame, Time, Location,\nRisk, Description)"]
        R2["Similarity Ranked\nResults with\nRelevance Score"]
    end

    Q1 --> S1
    Q2 --> S2
    Q3 --> S1
    Q4 --> S1 & S2

    S1 --> R1
    S2 --> R2
```

**Query types supported:**

| Query Type | Engine | Example |
|------------|--------|---------|
| Object search | SQLite | `--object "truck"` |
| Time range | SQLite | `--time "after 22:00"` |
| Location | SQLite | `--location "Main Gate"` |
| Suspicious only | SQLite | `--suspicious` |
| Alert log | SQLite | `--alerts` |
| Natural language | ChromaDB | `--search "suspicious nighttime activity"` |
| Session stats | SQLite | `--summary` |

---

## 📦 Module Breakdown

### Simulators (`simulators/`)

```mermaid
flowchart LR
    subgraph frames.py
        F["30 Frames\n(24hr patrol)"]
        F --> F1["06:00-08:00\nShift start\nEmployee arrivals"]
        F --> F2["08:00-14:00\nBusiness hours\nDeliveries"]
        F --> F3["14:00-22:00\nAfternoon\nSuspicious activity"]
        F --> F4["22:00-01:00\nNight\nBreach attempts"]
    end

    subgraph telemetry.py
        T["TelemetrySimulator"]
        T --> T1["Battery: 100% → 10%\n(1-3% drain/frame)"]
        T --> T2["Altitude: 8-25m\n(varies by location)"]
        T --> T3["Wind: 1-15 km/h\n(calmer at night)"]
        T --> T4["GPS: strong/moderate\n(10% chance moderate)"]
    end
```

### Analysis (`analysis/vlm_analyzer.py`)

The VLM Analyzer sends each frame description to **GPT-4o-mini** with a detailed security analyst system prompt. It returns structured JSON:

```json
{
    "objects": ["Person in dark hoodie", "Backpack"],
    "event_type": "suspicious_activity",
    "risk_level": "high",
    "is_suspicious": true,
    "description": "Unidentified person near perimeter fence taking photos",
    "recommended_action": "Dispatch security"
}
```

If the API fails, a **fallback parser** uses keyword matching to extract basic analysis from the description text.

### Object Detection (`detector.py`)

The `VideoDetector` class uses **Grounding DINO** (via HuggingFace Transformers) with **DeepSORT** tracking:

- **Open-vocabulary detection** — detect any object by text prompt, no fixed class limit
- **28+ security-focused classes** — person, car, truck, weapon, knife, gun, fire, smoke, drone, fence, gate, door, etc.
- **Dynamic prompts** — change what you detect at runtime with `set_prompt()`
- **Persistent tracking IDs** — same object keeps its ID across frames via DeepSORT
- **Color-coded bounding boxes** — orange for people, red for weapons, magenta for drones
- **Confidence threshold** — configurable (default 0.3 for video, 0.4 for live)
- **Zero-shot** — no retraining needed to detect new object types

### Agent (`agent/`)

```mermaid
flowchart TD
    A["SecurityAgent\n(LangGraph ReAct)"] --> B["GPT-4o-mini LLM\n(temperature=0.1)"]
    A --> C["Conversation Memory\n(last 20 messages)"]
    A --> D["4 Custom Tools"]

    D --> D1["log_event\n→ SQLite + ChromaDB\n→ Vehicle tracking"]
    D --> D2["check_alert_rules\n→ 8 rules evaluation\n→ Alerts to DB"]
    D --> D3["query_past_events\n→ SQLite keyword search\n→ ChromaDB semantic search"]
    D --> D4["generate_summary\n→ Session statistics\n→ Alert details\n→ Suspicious activity log"]

    B --> E["ReAct Loop:\n1. Observe frame\n2. Think about risks\n3. Call tools\n4. Respond"]

    C --> E
```

The agent uses a **ReAct (Reason + Act)** loop — it observes each frame's analysis, reasons about security implications, calls the appropriate tools, and produces an actionable security assessment. It maintains memory of previous frames to detect patterns like:
- **Vehicle re-entry** — same vehicle seen multiple times
- **Loitering** — person in consecutive frames near restricted area  
- **Threat escalation** — person near fence → person climbing fence

---

## 🚨 Alert Rules Engine

The `AlertManager` evaluates **8 configurable rules** against each frame:

| # | Rule | Severity | Trigger Condition |
|---|------|----------|-------------------|
| 1 | `after_hours_person` | 🟠 HIGH | Person detected between 22:00–06:00 |
| 2 | `perimeter_breach` | 🔴 CRITICAL | Person near fence + breach indicators (climb, cut, test) |
| 3 | `unauthorized_access` | 🔴 CRITICAL | No badge/ski mask near server room, warehouse, loading dock |
| 4 | `unknown_vehicle_night` | 🟠 HIGH | Unrecognized vehicle after hours |
| 5 | `vehicle_reentry` | 🟡 MEDIUM | Same vehicle seen >1 time (possible surveillance) |
| 6 | `suspicious_behavior` | 🟠 HIGH | Keywords: loitering, photographing, circling, casing |
| 7 | `door_anomaly` | 🟡 MEDIUM | Door open/ajar outside normal hours |
| 8 | `unauthorized_parking` | 🟢 LOW | Vehicle in unauthorized parking zone |

```mermaid
flowchart TD
    A["Frame Analysis Input"] --> B{"Is it after hours?\n(22:00-06:00)"}

    B -- "Yes" --> C{"Person detected?"}
    C -- "Yes" --> C1["🟠 ALERT: after_hours_person"]

    B -- "Yes" --> D{"Vehicle detected?"}
    D -- "Yes" --> D1{"Known vehicle?"}
    D1 -- "No" --> D2["🟠 ALERT: unknown_vehicle_night"]

    A --> E{"Near perimeter fence?"}
    E -- "Yes" --> E1{"Person + breach indicators?"}
    E1 -- "Yes" --> E2["🔴 ALERT: perimeter_breach"]

    A --> F{"Near restricted area?"}
    F -- "Yes" --> F1{"No badge / ski mask?"}
    F1 -- "Yes" --> F2["🔴 ALERT: unauthorized_access"]

    A --> G{"Suspicious keywords?"}
    G -- "Yes" --> G1["🟠 ALERT: suspicious_behavior"]

    A --> H{"Door open/ajar?"}
    H -- "Yes" --> H1["🟡 ALERT: door_anomaly"]

    A --> I{"Vehicle seen before?"}
    I -- "Yes (count > 1)" --> I1["🟡 ALERT: vehicle_reentry"]

    A --> J{"Unauthorized parking?"}
    J -- "Yes" --> J1["🟢 ALERT: unauthorized_parking"]
```

---

## 🗄️ Dual Database Architecture

```mermaid
flowchart LR
    subgraph SQLite["SQLite (Structured)"]
        direction TB
        ST1["frames table\n• frame_id, timestamp\n• location, objects\n• event_type, risk\n• is_suspicious"]
        ST2["alerts table\n• severity, rule_name\n• message, location"]
        ST3["vehicle_log table\n• vehicle_description\n• entry_count\n• locations visited"]
    end

    subgraph ChromaDB["ChromaDB (Semantic)"]
        direction TB
        CH1["drone_frames collection\n• Embedded documents\n• Vector similarity\n• Metadata filtering"]
    end

    Q1["Search: 'truck'"] --> SQLite
    Q2["Search: 'suspicious\nnighttime activity\nnear the fence'"] --> ChromaDB
    Q3["Time: 'after 22:00'"] --> SQLite
    Q4["All alerts"] --> SQLite
```

| Feature | SQLite | ChromaDB |
|---------|--------|----------|
| **Query Type** | Keyword, time, location, exact match | Natural language, semantic similarity |
| **Speed** | Very fast (indexed SQL) | Fast (vector ANN search) |
| **Use Case** | "Show all trucks" / "Alerts after 10pm" | "Suspicious activity near fence at night" |
| **Storage** | `data/security_events.db` | ChromaDB Cloud (or local `data/chroma_db/` fallback) |

---

## 🖥️ Web Dashboard — Aegis Drone Command

The web dashboard (`server.py` + `static/`) provides a military-industrial command center UI with 5 pages:

| Page | File | Description |
|------|------|-------------|
| **Live Feed** | `index.html` | Real-time simulation with SSE streaming, metrics, frame log |
| **Video Analysis** | `video.html` | Upload video → Grounding DINO + Vision AI detection with operational log |
| **Alerts** | `alerts.html` | Alert dashboard with severity filtering |
| **Query Frames** | `query.html` | Keyword + semantic search with filters |
| **Daily Summary** | `summary.html` | AI-generated security briefing |

---

## 📡 API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Serve main dashboard |
| `GET` | `/health` | Health check (keep-alive endpoint) |
| `GET` | `/api/status` | Current simulation state |
| `GET` | `/api/simulate` | **SSE** — Start patrol simulation, stream results |
| `POST` | `/api/halt` | **Emergency halt** — stop running simulation immediately |
| `POST` | `/api/reset` | Force-reset simulation state |
| `GET` | `/api/alerts?severity=CRITICAL` | Get alerts, optional severity filter |
| `GET` | `/api/frames` | Get all processed frames |
| `GET` | `/api/frames/search?q=truck&risk=HIGH` | Search frames by keyword + risk |
| `GET` | `/api/semantic?q=suspicious+activity` | ChromaDB semantic search |
| `GET` | `/api/summary` | Get current session summary |
| `POST` | `/api/generate_summary` | Generate fresh AI summary |
| `POST` | `/api/analyze_video` | **SSE** — Upload video for dual detection |
| `GET` | `/api/stats` | Database statistics |

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+**
- **OpenAI API Key** (for GPT-4o-mini)

### Setup

```bash
# Clone the repository
cd "Drone Scecurity Analyst Agent"

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Configure API key
copy .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### Run Options

```bash
# Option 1: Web Dashboard (recommended)
python server.py
# Open http://localhost:8000

# Option 2: CLI Monitoring Pipeline
python main.py

# Option 3: Streamlit Dashboard
streamlit run app.py

# Option 4: Query past events
python query.py --object "truck"
python query.py --search "suspicious nighttime activity"
python query.py --alerts
python query.py --summary
```

---

## 📁 Project Structure

```
Drone Security Analyst Agent/
│
├── server.py                  # FastAPI backend + REST API + SSE endpoints
├── app.py                     # Streamlit dashboard (alternative UI)
├── main.py                    # CLI monitoring pipeline
├── query.py                   # CLI query interface (7 query types)
├── config.py                  # Central config (API keys, paths, constants)
├── detector.py                # Grounding DINO + DeepSORT video object detector
├── requirements.txt           # Python dependencies
├── .env                       # API keys (gitignored)
│
├── simulators/
│   ├── frames.py              # 30 simulated drone frames (24hr cycle)
│   └── telemetry.py           # GPS, altitude, battery, wind simulation
│
├── analysis/
│   └── vlm_analyzer.py        # GPT-4o-mini frame analysis → structured JSON
│
├── agent/
│   ├── security_agent.py      # LangGraph ReAct agent with memory
│   ├── tools.py               # 4 custom LangChain tools
│   └── prompts.py             # System prompts for agent behavior
│
├── indexing/
│   ├── sqlite_store.py        # SQLite structured storage (3 tables)
│   └── chroma_store.py        # ChromaDB semantic vector search
│
├── alerts/
│   └── rules_engine.py        # 8 configurable alert rules
│
├── static/
│   ├── index.html             # Live Feed page
│   ├── video.html             # Video Analysis page
│   ├── alerts.html            # Alert Dashboard page
│   ├── query.html             # Query Frames page
│   ├── summary.html           # Daily Summary page
│   └── shell.js               # Shared navigation + sidebar shell
│
├── tests/
│   ├── test_telemetry.py      # Telemetry simulator tests
│   ├── test_alerts.py         # Alert rules engine tests (10 tests)
│   ├── test_indexing.py       # SQLite + ChromaDB tests
│   └── test_agent.py          # Agent tool integration tests
│
├── docs/
│   ├── architecture.md        # Architecture document
│   └── feature_spec.md        # Feature specification
│
└── data/                      # Generated at runtime
    ├── security_events.db     # SQLite database
    └── chroma_db/             # ChromaDB vector store
```

---

## 🔧 Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| LLM Backend | GPT-4o-mini | Fast inference, vision capability, good JSON output, cost-effective |
| Agent Framework | LangGraph ReAct | Industry standard, tool-calling, memory management, reasoning loop |
| Object Detection | Grounding DINO + DeepSORT | Open-vocabulary zero-shot detection, text-prompted, persistent tracking IDs |
| Structured DB | SQLite | Zero-config, built into Python, fast keyword/time queries |
| Vector DB | ChromaDB Cloud | Managed cloud storage with local fallback, built-in embeddings |
| Dual Detection | Grounding DINO + Vision API | Open-vocabulary bounding boxes + contextual scene understanding |
| Web Framework | FastAPI + SSE | Async, real-time streaming, auto-generated API docs |
| Console UX | Rich library | Professional colored output, tables, progress bars |
| Memory | Last 20 messages | Cross-frame context for pattern recognition without token overflow |
| Emergency Control | /api/halt + SSE events | Real-time simulation halt with proper UI state cleanup |

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_alerts.py -v
pytest tests/test_indexing.py -v
```

**Test coverage:**
- `test_telemetry.py` — Battery drain, altitude ranges, wind simulation
- `test_alerts.py` — All 8 alert rules with positive/negative cases (10 tests)
- `test_indexing.py` — SQLite CRUD, ChromaDB semantic search, vehicle tracking
- `test_agent.py` — Agent tool calling, LangGraph integration

---

## 🤖 AI Tools Used

- **OpenAI GPT-4o-mini** — Frame analysis (VLM) and agent reasoning
- **LangChain + LangGraph** — Agent orchestration, tool management, ReAct loop
- **Grounding DINO** (HuggingFace Transformers) — Open-vocabulary zero-shot object detection via text prompts
- **DeepSORT** — Multi-object tracking with persistent IDs
- **ChromaDB Cloud** — Managed semantic vector embeddings with local fallback

---

## 🔮 Future Improvements

- Real video input with OpenCV and actual camera feeds
- Multi-drone support with coordinated patrol routes
- SAM 2 segmentation for pixel-level object masking
- VideoMAE for action understanding and behavior analysis
- Integration with real alert systems (SMS, email, Slack)
- Geofencing with GPS-based zone definitions
- Historical pattern analysis with time-series ML models
- WebSocket-based real-time drone telemetry streaming

---

## 📝 License

MIT License
