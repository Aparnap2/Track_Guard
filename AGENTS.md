# AGENTS.md - IterateSwarm Coding Guidelines

## Project Overview

**Go + Python ChatOps platform** with Temporal orchestration and HTMX UI.

**Tech Stack:**
- **Go Core** (`apps/core/`): Go 1.24, Fiber, sqlc, Temporal SDK, HTMX
- **Python** (`apps/ai/`): Python 3.13, LangGraph, DSPy, Pydantic
- **LLM Providers**: OpenAI-compatible SDK (Azure AI Foundry, Groq, Ollama)
- **Infrastructure**: Docker (Temporal, Qdrant, PostgreSQL)

---

## V4.0 Status

| Component | Status | Notes |
|-----------|--------|-------|
| Python Tests | ✅ 319/320 passing | 1 pre-existing timeout in curator_graphiti |
| Go Build | ✅ Clean | Binary compiles successfully |
| Go HTMX Handler Tests | ✅ 74+ passing | command center (19), business handlers (13), founder (14), plus LLMops, onboarding, watchlist, telegram, razorpay |
| HTMX Routes | ✅ 13+ routes | Command center dashboard panels + SSE endpoints |
| SSE Streaming | ✅ | HTMX `hx-ext="sse"` + `SetBodyStreamWriter` pattern + SSEHub event-type filtering |
| SSEHub Event-Type Filtering | ✅ | `Subscribe(tenantID, eventTypes...)` with per-subscriber channels (buffered 64) |
| Specialist Agents | ✅ | Finance, Data, Ops (each with LangGraph graph + Temporal workflow) |
| HITL Temporal Signals | ✅ | `SignalWorkflow("hitl-approval")` unblocks `AwaitWithTimeout` |
| MissionState Write Path | ✅ | `POST /api/mission-state` from Python AI → PostgreSQL |
| @mention Routing | ✅ | `map[string]specialistRoute` — O(1) map lookup, 9 aliases → 6 workflows |
| Tool Calling Surface | ✅ | `apps/ai/src/agents/tools/` — ToolDef, TOOL_REGISTRY, 4 tools with HITL tier mapping |
| ACE Reflector Loop | ✅ | Slack button clicks → `score_from_button()` + `update_strategy_confidence()` |
| MissionState Promotion | ✅ | Added `prepared_brief`, `pending_decisions`, `last_updated_by` fields |
| DB Tests | 🟡 Skip | Requires PostgreSQL container |
| Webhook Tests | 🟡 Skip | Requires Redpanda container |

---

## Build/Lint/Test Commands

### Go (apps/core/)

```bash
# Download dependencies
go mod download

# Run all tests
go test ./...

# Run tests for specific package
go test ./internal/agents/...

# Run single test
go test ./internal/agents/... -run TestTriageAgent -v

# Format code
go fmt ./...

# Build worker
mkdir -p bin
go build -o bin/worker ./cmd/worker
go build -o bin/server ./cmd/server

# Run server
go run cmd/server/main.go

# Run worker
go run cmd/worker/main.go
```

### Makefile

```bash
# Start all services
make up

# Stop services
make down

# Build all
make build

# Generate protobuf code
make proto
```

### Python (apps/ai/)

```bash
# Install dependencies (requires uv)
cd apps/ai
uv sync

# Run all tests
uv run pytest tests/ -v

# Run specific test suite
uv run pytest tests/test_session.py -v
uv run pytest tests/test_cofounder.py -v
uv run pytest tests/test_guardian.py -v
uv run pytest tests/test_slackbot.py -v
uv run pytest tests/test_curator_graphiti.py -v  # 1 pre-existing timeout

# Run with coverage
uv run pytest tests/ --cov=src --cov-report=term-missing
```

---

## Code Style Guidelines

### Go (Core Service)

**Imports:**
- Standard library first
- Third-party packages second
- Internal packages last with full module path
- Group imports with blank lines between groups

**Formatting:**
- `go fmt` standard formatting
- Use goimports for import organization

**Types:**
- Explicit types on struct fields
- Return concrete types, accept interfaces
- Use meaningful type names

**Naming:**
- `camelCase` for unexported identifiers
- `PascalCase` for exported identifiers
- `SCREAMING_SNAKE_CASE` for constants
- Acronyms: all caps (HTTP, URL, ID, SSE, HITL)

**Error Handling:**
- Check errors immediately: `if err != nil`
- Return errors up the call stack
- Wrap errors with context: `fmt.Errorf("context: %w", err)
- Use fiber.Error for HTTP status codes

**Struct Tags:**
- JSON tags: `json:"field_name,omitempty"`
- Database tags from sqlc generated code
- Form tags: `form:"field_name"`

**Logging:**
- Use internal/logging package
- Structured logging with key-value pairs
- Log at appropriate levels (Info, Warn, Error)

**SSE Pattern:**
- Use Fiber v2 `SetBodyStreamWriter` with `*bufio.Writer`
- Named SSE events: `event: chat`, `event: heartbeat`, `event: connected`
- Non-blocking broadcast: `tryBroadcast()` with `select { case ch <- msg: default: log }`
- HTMX declarative: `hx-ext="sse"` + `sse-connect` + `sse-swap` + `hx-swap`
- HTML fragments as SSE data payload (server-rendered via `renderChatBubble()`)
- Always `html.EscapeString()` on user/LLM text for XSS protection
- SSEHub event-type filtering: `Subscribe(tenantID, eventTypes...)` + `Broadcast(tenantID, SSEEvent)`

**Goroutine Safety:**
- `sync.WaitGroup` for tracking in-flight workflow dispatches
- Context cancellation via `c.Context().Done()` in SSE handlers
- 5-minute context timeout for workflow dispatch goroutines
- Non-blocking channel sends with `select/default` to prevent goroutine pile-up

**Specialist Route Map Pattern:**
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
- O(1) map lookup replaces if-else chain
- Adding a specialist = 1 map entry + 1 Python workflow class
- 9 aliases → 6 workflows (QA, Finance, Data, Ops, Comms, Hiring)

### SQL (sqlc)

**Schema:**
- Place in `internal/db/schema.sql`
- Use `IF NOT EXISTS` for idempotent migrations
- Include indexes for frequently queried columns

**Queries:**
- Place in `internal/db/queries/`
- Name queries with action prefix: `-- name: {Action}{Entity} :{one|many}`
- Use `@param` notation for parameters

### Protobuf

**Generation:**
- Source files in `proto/` directory
- Generated code goes to `gen/go/`
- Use `buf generate` for code generation

---

## Project Structure

```
apps/
  core/              # Go Modular Monolith
    cmd/
      server/        # HTTP server entrypoint
      worker/        # Temporal worker entrypoint
    internal/
      web/           # HTTP handlers (Fiber + HTMX + SSE)
        handler.go   # All endpoints, @mention routing, SSE broadcast
        sse.go       # Legacy SSE handler with DB polling
        command_center_test.go  # 52+ tests
        templates/
          command_center.html       # Main dashboard
          partials/                 # HTMX partials (13+ panels)
            command_chat.html        # Chat with hx-ext="sse"
            command_approvals.html   # Approval queue (approve/hold)
            command_mission_state.html
      agents/        # Go agent definitions
      config/        # LLM configuration
      db/            # sqlc generated code
      database/      # Connection utilities
      temporal/      # Temporal client (SignalWorkflow, ExecuteWorkflow)
      workflow/      # Temporal workflows & stubs (cleaned)
    sqlc.yaml       # sqlc configuration
  ai/                # Python AI Worker
    src/
      agents/        # Agent definitions
        pulse/       # PulseAgent (daily business pulse)
        anomaly/     # AnomalyAgent (explains spikes)
        investor/    # InvestorAgent (weekly updates)
        qa/          # QAAgent (founder Q&A)
        comms/       # CommsTriageAgent
        hiring/      # HiringAgent
        base/        # Abstract agent class, tool framework
        finance/     # V4 NEW — Finance specialist (FinanceGraph)
        data/        # V4 NEW — Data specialist (DataGraph)
        ops/         # V4 NEW — Ops specialist (OpsGraph)
        tools/       # V4 NEW — ToolRegistry + 4 ToolDef implementations
          __init__.py          # ToolDef, TOOL_REGISTRY, register_tool(), auto-import
          pause_payment_retry.py    # FG-05: pause Stripe retry (review)
          draft_investor_update.py  # Schedule: draft investor email (approve)
          schedule_customer_checkin.py  # FG-03/BG-04: at-risk checkin (auto)
          flag_churn_risk.py        # BG-06/BG-04: flag churn segment (auto)
      workflows/     # V4 NEW — Temporal workflow definitions
        finance_workflow.py
        data_workflow.py
        ops_workflow.py
      business/      # V3.0 MBA integration
      predictive/    # V3.0 Forecasting engine
      activities/    # Temporal activities
      orchestration/ # Pipeline orchestrators
      services/      # Trust battery, alert gate
      session/       # MissionState, relevance gate
      guardian/      # Watchlist, detector, assemblers
      integrations/  # Stripe, Plaid, Slack, ERPNext, HubSpot, QuickBooks
      memory/        # Graphiti, Qdrant, spine
      schemas/       # Pydantic models
      events/        # Redis Streams event bus
    tests/           # Pytest test suite (319+ tests)
    pyproject.toml   # Python dependencies
```

---

## Key Conventions

1. **Feature Branches**: Use `git checkout -b feature/description`
2. **Commits**: Use Conventional Commits (`feat:`, `fix:`, `refactor:`)
3. **Never commit to main**
4. **Environment**: Use `.env` file for secrets (never commit)
5. **Database**: Use sqlc for type-safe SQL; regenerate after schema changes

---

## LLM Configuration

The system uses the **official OpenAI Go SDK v3** which is compatible with:

- **Azure AI Foundry**: Set `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_API_KEY`
- **Groq**: Set `GROQ_API_KEY`
- **OpenAI**: Set `OPENAI_API_KEY`
- **Ollama**: Set `OLLAMA_BASE_URL` and `OLLAMA_API_KEY` (local)

Configuration is auto-detected. See `internal/config/llm.go`.
