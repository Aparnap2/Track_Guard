# Sarthi — AI Coordination Layer for Solo Founders

> Server-rendered command center with SSE push, goroutine-based Temporal dispatch, and Python specialist agents.
> Chat → @mention → specialist workflow → SSE result — all driven by Go + Temporal + LangGraph.

[![Tests](https://img.shields.io/badge/tests-371%20passing-brightgreen)](#)
[![Architecture](https://img.shields.io/badge/architecture-SSE%20%2B%20Specialist-blue)](#)
[![Go](https://img.shields.io/badge/Go-1.24-blue?logo=go)](#)
[![Python](https://img.shields.io/badge/Python-3.13-green?logo=python)](#)

---

## The Architecture: SSE-First Command Center

Browser connects via HTMX SSE. Go dispatches to Temporal in goroutines. Python specialist agents handle each domain.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Browser (HTMX + SSE)                            │
│  ┌──────────────────────────┐    ┌───────────────────────────────┐          │
│  │  command_chat.html        │    │  command_approvals.html       │          │
│  │  hx-ext="sse"             │    │  Approve / Hold buttons      │          │
│  │  sse-connect="/api/...    │    │  → Temporal Signal           │          │
│  └──────────┬────────────────┘    └───────────┬───────────────────┘          │
│             │ SSE event:chat                   │ POST approve/hold            │
└─────────────┼──────────────────────────────────┼─────────────────────────────┘
              │                                  │
              ▼                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Go Core (Fiber v2)                                   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  Handler struct                                                        │   │
│  │  ┌─────────────┐  ┌───────────────┐  ┌──────────────┐                 │   │
│  │  │ chatBroadcast│  │ temporal      │  │ wg sync.     │                 │   │
│  │  │ chan fiber.Map│ │ *temporal.Client│ │ WaitGroup     │                 │   │
│  │  └──────┬──────┘  └───────┬───────┘  └──────────────┘                 │   │
│  │         │                 │                                            │   │
│  │  ┌──────▼──────┐  ┌──────▼───────┐                                    │   │
│  │  │ SSE endpoint │  │ specialist-  │                                    │   │
│  │  │ SetBodyStream│  │ Routes map   │                                    │   │
│  │  │ Writer       │  │ @mention→Wkfl│                                    │   │
│  │  │ renderChat-  │  │ + displayName│                                    │   │
│  │  │ Bubble()     │  └──────┬───────┘                                    │   │
│  │  └──────────────┘         │                                            │   │
│  │                           │ goroutine dispatch + tryBroadcast()        │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  API Routes                                                           │   │
│  │  GET  /api/command/chat/events  → SSE stream (chat bubbles)          │   │
│  │  POST /api/command/chat/send    → goroutine + Temporal dispatch      │   │
│  │  POST /api/command/approvals/:id/approve → SignalWorkflow("hitl...") │   │
│  │  POST /api/command/approvals/:id/hold   → DB update                  │   │
│  │  GET  /api/mission-state        → read from PostgreSQL               │   │
│  │  POST /api/mission-state        → write from Python AI               │   │
│  │  GET  /api/command/*            → dashboard partials (status, KPIs,  │   │
│  │                                    watchlist, timeline, approvals,   │   │
│  │                                    agent fleet, chart-data)           │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
              │ Temporal                         │ SQL / POST
              ▼                                  ▼
┌─────────────────────────────┐    ┌──────────────────────────────────────────┐
│  Temporal Server             │    │  PostgreSQL                                │
│  Task Queue:                 │    │  Tables:                                   │
│  TRACKGUARD-MAIN-QUEUE       │    │  - mission_state (Python AI writes)       │
│                              │    │  - planned_actions (HITL approval queue)  │
│  Workflows:                  │    │  - chat_messages (conversation history)   │
│  QAWorkflow                  │    │  - agent_traces (duration, tokens, cost)  │
│  FinanceWorkflow             │    │  - agent_events (SSE polling source)      │
│  DataWorkflow                │    │                                           │
│  OpsWorkflow                 │    └──────────────────────────────────────────┘
│  CommsWorkflow               │
│  HiringWorkflow              │
│                              │
│  Signals: "hitl-approval"    │
└──────┬──────────────────────┘
       │ Temporal activity dispatch
       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                    Python AI Worker (Temporal SDK + LangGraph)                 │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │  Temporal Workflow Definitions                                       │    │
│  │  FinanceWorkflow · DataWorkflow · OpsWorkflow · QAWorkflow           │    │
│  │  CommsWorkflow · HiringWorkflow                                      │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │  LangGraph Agent Graphs                                               │    │
│  │  FinanceGraph · DataGraph · OpsGraph · CommsGraph · HiringGraph       │    │
│  │                                    │                                   │    │
│  │  LLM Provider: Azure AI Foundry / Groq / Ollama (auto-detected)       │    │
│  │  Structured Output: instructor + Pydantic v2 (strict mode)            │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Chat Flow: @mention → Specialist Workflow → SSE Result

```
User types "@finance Q3 revenue?" → HTMX POST /api/command/chat/send
  → Go Handler extracts @mentions → matches in specialistRoutes map
  → Broadcasts user bubble via SSE (immediate)
  → go func() with sync.WaitGroup:
      → tryBroadcast() → "🤔 Thinking..." → SSE
      → Temporal ExecuteWorkflow("FinanceWorkflow", input)
      → Python workflow → LangGraph agent → LLM result
      → run.Get(ctx, &result) → renderChatBubble() → tryBroadcast() → SSE
```

### Key V4.0 Decisions (ADR-001)

| Decision | Benefit |
|----------|---------|
| **HTMX SSE** over WebSocket/Raw JS | ~40 fewer lines of JS. Auto-reconnect built-in. Server owns HTML rendering via `renderChatBubble()`. |
| **Goroutine dispatch** over synchronous `run.Get()` | No more 60s HTTP timeouts. "🤔 Thinking..." appears immediately. `sync.WaitGroup` for graceful shutdown. |
| **Map-based specialist routing** over if-else chain | `map[string]specialistRoute` — O(1) lookup. Adding a specialist = 1 map entry + 1 Python class. |
| **Temporal Signal for HITL** | Approval buttons actually unblock `AwaitWithTimeout` gates. End-to-end HITL. |
| **Server-rendered chat bubbles** | `html.EscapeString()` XSS protection. Agent color classes. Single source of truth for HTML. |
| **MissionState POST endpoint** | Python AI → POST → PostgreSQL → GET → Dashboard. Pure server-side rendered. |
| **Remove dead stubs** | Cleaned 40 lines of stale placeholder types from `workflow/stubs.go`. |

> Full details: [ADR-001: Sarthi v4.0 Architecture Evolution](.opencode/context/adr/001-sarthi-v4-architecture-evolution.md)

---

## Command Center Dashboard

13+ HTMX-driven screens in the command center:

| Dashboard Panel | Route | Auto-refresh |
|-----------------|-------|-------------|
| **Chat Panel** | `POST /api/command/chat/send` + SSE `GET /api/command/chat/events` | SSE push (instant) |
| **Approvals Queue** | `GET /api/command/approvals` + `POST approve/:id` | Poll + Signal |
| **Mission State** | `GET /api/command/mission-state` | On load |
| **Status Bar** | `GET /api/command/status` | 10s |
| **KPI Cards** | `GET /api/command/kpis` | 15s |
| **Watchlist** | `GET /api/command/watchlist` | 30s |
| **Timeline** | `GET /api/command/timeline` | 15s |
| **Agent Fleet** | `GET /api/command/agent-fleet` | 30s |
| **Chart Data** | `GET /api/command/chart-data` (JSON) | On demand |
| **Dashboard Heartbeat** | `GET /api/command/events` (SSE) | Push |

### Specialist Route Map

```go
var specialistRoutes = map[string]specialistRoute{
    "@sarthi":  {"QAWorkflow", "Sarthi"},
    "@agent":   {"QAWorkflow", "Sarthi"},
    "@qa":      {"QAWorkflow", "Sarthi"},
    "@ask":     {"QAWorkflow", "Sarthi"},
    "@finance": {"FinanceWorkflow", "Finance"},
    "@data":    {"DataWorkflow", "Data"},
    "@ops":     {"OpsWorkflow", "Ops"},
    "@comms":   {"CommsWorkflow", "Comms"},
    "@hiring":  {"HiringWorkflow", "Hiring"},
}
```

---

## Core Components

### Specialist Agent System
6 workflow types dispatched from the Go core via Temporal:
- **Finance** — MRR/burn analysis, anomaly detection via FinanceGraph
- **Data** — query, transform, aggregate via DataGraph
- **Ops** — deploy, monitor, alert via OpsGraph
- **Comms** — draft, notify, summarize via CommsGraph
- **Hiring** — search, screen, evaluate via HiringGraph
- **QA (Sarthi/Agent)** — general Q&A routed to QAWorkflow

### HITL with Temporal Signals
- AI proposes action → `planned_actions` row created with `status=pending`
- Temporal workflow reaches `AwaitWithTimeout("hitl-approval", 48h)`
- User clicks Approve → POST → `SignalWorkflow(ctx, id, "hitl-approval", true)`
- Workflow unblocks, execution continues

### MissionState Write Path
- **Python AI** compiles operational state (MRR, burn, health, signals)
- **POST** to `/api/mission-state` → **PostgreSQL** (`mission_state` table)
- **GET** → Go templates → HTML (dashboard)
- Pure server-side rendered — no client state

### SSE Chat System
- HTMX `hx-ext="sse"` declaratively subscribes to SSE stream
- Server sends `event: chat` with HTML fragments as data payload
- `renderChatBubble()` with `html.EscapeString()` — XSS-safe
- Agent color classes: `agent-sarthi` (blue), `agent-finance` (green), `agent-data` (purple), `agent-ops` (yellow)
- Non-blocking `tryBroadcast()` with `select/default` on buffered channel (capacity 100)
- Two SSE endpoints: chat-specific and dashboard heartbeat

### Goroutine Safety Patterns
- `sync.WaitGroup` for graceful shutdown tracking of in-flight workflow dispatches
- Context cancellation via `c.Context().Done()` in SSE handlers
- 5-minute context timeout merged from request context for workflow dispatch
- `select { case ch <- msg: default: log }` prevents goroutine pile-up

### V3.0 Legacy: MBA Integration Layer
The V3.0 deterministic business logic layer (Finance Rules, Guardrails Engine, Predictive Guardian, Startup Guardian) remains operational as a background pipeline. See historical sections below for full documentation.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Go Core** | Go 1.24 + Fiber v2 + HTMX |
| **Python AI** | Python 3.13 + Temporal SDK + LangGraph + DSPy |
| **Workflow Engine** | Temporal (1.39 SDK) |
| **LLM** | Azure AI Foundry / Groq / Ollama (auto-detected via OpenAI SDK) |
| **Structured Output** | instructor + Pydantic v2 (strict mode) |
| **Relational DB** | PostgreSQL (MissionState, chat, approvals, traces) |
| **Vector Store** | Qdrant (agent memory, semantic search) |
| **Cache** | Redis (session state, working memory) |
| **Observability** | Langfuse v4 (LLM tracing) |
| **Config** | Env-only via pydantic-settings — zero hardcoded secrets |

---

## Test Coverage (371+ Passing — Go Build Clean)

| Suite | Tests | Status |
|-------|-------|--------|
| Python Unit Tests | 319 | ✅ (1 pre-existing timeout in curator_graphiti skipped) |
| Go HTMX Web Handlers | 52 | ✅ |
| Go Build | Clean | ✅ |
| DB Tests | 🟡 Skip | Requires PostgreSQL container |
| Redpanda Tests | 🟡 Skip | Requires Redpanda container |

**Python Suites (319 tests):**
- Session Layer, Co-founder Agent, Correlation + Avoidance
- Guardian Watchlist (Finance, BI, Ops), Finance Guardian
- Memory Spine (Graphiti), HITL, Finance Rules, Guardrails Engine
- Business Pipeline, Predictive Guardian (engine + activity)
- Startup Guardian (Connectors, Assemblers, Watchlists, Correlations, Detector, Orchestrator, E2E)
- Deterministic Trajectory (87), State Machine (17), Edge Cases (47), Contracts (68), Mockoon (17)
- All Others (100+)

**Go Web Handler Suites (52 tests):**
- Command Center (chat, approvals, mission state)
- SSE streaming endpoints
- @mention routing and specialist dispatch
- HITL approval signal flow
- Template rendering

---

## Project Structure

```
apps/
  core/                    # Go Modular Monolith
    cmd/
      server/              # HTTP server entrypoint
      worker/              # Temporal worker entrypoint
    internal/
      web/                 # HTTP handlers + HTMX templates
        handler.go         # All HTTP handlers, @mention routing, SSE broadcast
        sse.go             # Legacy SSE handler with DB polling
        command_center_test.go  # 52+ tests
        templates/
          command_center.html       # Main dashboard
          partials/                  # 13+ HTMX partials
            command_chat.html        # Chat panel with hx-ext="sse"
            command_approvals.html   # Approval queue UI
            command_mission_state.html
      agents/              # Go agent definitions
      workflow/            # Temporal workflows, stubs (cleaned)
      temporal/            # Temporal client wrapper (SignalWorkflow, ExecuteWorkflow)
      api/                 # HTTP handlers (Fiber + HTMX)
      config/              # LLM configuration
      db/                  # sqlc generated code
      database/            # Connection utilities
  ai/                      # Python AI Worker
    src/
      agents/              # Guardian agents (V1-3 legacy)
        pulse/             # PulseAgent (daily business pulse)
        anomaly/           # AnomalyAgent (explains spikes)
        investor/          # InvestorAgent (weekly updates)
        qa/                # QAAgent (founder Q&A)
        comms/             # CommsTriageAgent
        hiring/            # HiringAgent
        base/              # Abstract agent class, tool framework
        finance/           # Finance specialist (V4 NEW — FinanceGraph)
        data/              # Data specialist (V4 NEW — DataGraph)
        ops/               # Ops specialist (V4 NEW — OpsGraph)
      business/            # V3.0 MBA integration (Finance Rules, Guardrails)
      predictive/          # V3.0 Forecasting engine
      workflows/           # V4 NEW — Temporal workflow definitions
        finance_workflow.py    # FinanceWorkflow
        data_workflow.py       # DataWorkflow
        ops_workflow.py        # OpsWorkflow
      activities/          # Temporal activities
      orchestration/       # Pipeline orchestrators (V3 legacy + V4)
      services/            # Trust battery, alert gate, decision engine
      session/             # MissionState, relevance gate
      guardian/            # Watchlist, detector, assemblers
      integrations/        # Stripe, Plaid, Slack, ERPNext, HubSpot, QuickBooks
      memory/              # Graphiti, Qdrant, spine
      schemas/             # Pydantic models
      events/              # Redis Streams event bus
    tests/
      unit/                # 319+ tests
    infrastructure/        # SQL migrations
```

---

## Quick Start

```bash
# Start infrastructure
docker start sarthi-postgres sarthi-qdrant sarthi-redis

# Run Python tests
cd apps/ai && uv run pytest tests/ -v

# Run Go web handler tests
cd apps/core && go test ./internal/web/... -v

# Start Python Temporal worker
cd apps/ai && uv run python -m src.worker

# Start Go server
cd apps/core && go run cmd/server/main.go

# Verify SSE chat works
# Open http://localhost:8080/command
# Type "@finance What's my current burn?" → see "🤔 Thinking..." → see answer
```

### SSE Chat Verification
1. Start services: `docker start sarthi-postgres sarthi-redis sarthi-qdrant`
2. Start Temporal: `docker start sarthi-temporal` (or `make up`)
3. Start Python worker: `cd apps/ai && uv run python -m src.worker`
4. Start Go server: `cd apps/core && go run cmd/server/main.go`
5. Open `http://localhost:8080/command` in browser
6. Select `@finance` from dropdown, type a question, click Send
7. You should see: your message → "🤔 Thinking..." → Finance's answer

---

## Development Principles

1. **Decision latency** — every feature must shorten the time between signal and action
2. **SSE-first** — push over pull; real-time streams over polling
3. **Exception quality** — high trust beats high volume; reduce false positives
4. **Founder cognition** — fewer, sharper, more actionable messages
5. **Trust gradually** — copilot → workflow assistant → semi-autonomous → autonomous
6. **No hardcoded secrets** — env-only configuration, centralized in `config/database.py`
7. **Composition over inheritance** — new packages import and nest existing schemas, never modify them
8. **Deterministic core** — finance, guardrails, and forecasting are pure Python with zero LLM calls
