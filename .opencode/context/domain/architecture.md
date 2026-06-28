# IterateSwarm Architecture

> **Purpose**: Document the current system architecture — Go modular monolith for core, Python AI worker for agents, Temporal for orchestration, PostgreSQL for state.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  Browser (HTMX + SSE + Chart.js)                                │
│  GET /command → command_center.html                             │
└───────────────────┬─────────────────────────────────────────────┘
                    │ hx-get / hx-post / hx-ext="sse"
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│  Go Core (apps/core/) — Fiber v2 HTTP Server                    │
│                                                                  │
│  ┌─────────────────────┐  ┌────────────────────────────────┐   │
│  │  handler.go          │  │  SSE (sse.go + handler.go)      │   │
│  │  • Dashboard, Feed   │  │  • SetBodyStreamWriter pattern  │   │
│  │  • HITL Queue (crud) │  │  • APICommandChatEvents (chat)  │   │
│  │  • Agent Map, Tasks  │  │  • APICommandEvents (dash)      │   │
│  │  • Config, Telemetry │  │  • AgentEvent polling (sse.go)  │   │
│  │  • Command Center:   │  │                                  │   │
│  │    Status, KPIs,     │  │  Temporal Client (temporal/)    │   │
│  │    MissionState,     │  │  • ExecuteWorkflow               │   │
│  │    Watchlist,        │  │  • SignalWorkflow (HITL)        │   │
│  │    Timeline,         │  │                                  │   │
│  │    Approvals, Chat   │  │  DB (database/ + db/)           │   │
│  │  • @mention routing  │  │  • sqlc generated queries       │   │
│  └─────────────────────┘  │  • Raw SQL via lib/pq             │   │
│                            └────────────────────────────────┘   │
└───────────────────┬─────────────────────────────────────────────┘
                    │ Temporal ExecuteWorkflow / SignalWorkflow
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│  Temporal Server                                                │
│  Task Queue: TRACKGUARD-MAIN-QUEUE                              │
│  Orchestrates Go activities + Python workflows                  │
└───────────────────┬─────────────────────────────────────────────┘
                    │ Worker picks up workflow tasks
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│  Python AI Worker (apps/ai/)                                    │
│                                                                  │
│  ┌─────────────────────┐  ┌────────────────────────────────┐   │
│  │  Specialist Agents   │  │  LangGraph Agent Graphs        │   │
│  │                      │  │  • FinanceGraph (finance)      │   │
│  │  FinanceWorkflow     │  │  • DataGraph (data)            │   │
│  │  DataWorkflow        │  │  • OpsGraph (ops)              │   │
│  │  OpsWorkflow         │  │  • (Comms, Hiring, QA — TBD)   │   │
│  │  CommsWorkflow (TBD) │  │                                  │   │
│  │  HiringWorkflow(TBD) │  │  LLM Provider: Groq (Ollama)    │   │
│  │  QAWorkflow (TBD)    │  │  Structured Output: instructor  │   │
│  └─────────────────────┘  └────────────────────────────────┘   │
└───────────────────┬─────────────────────────────────────────────┘
                    │ Writes mission_state, planned_actions, agent_traces
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│  PostgreSQL                                                      │
│  Tables: mission_state, planned_actions, agent_traces,          │
│          chat_messages, hitl_queue, agent_outputs               │
└─────────────────────────────────────────────────────────────────┘
```

> **Architecture decisions documented in:** [ADR-001: Sarthi v4.0 Architecture Evolution](../adr/001-sarthi-v4-architecture-evolution.md)

## Key Design Decisions

### Go Modular Monolith (apps/core/)

- **Framework**: Fiber v2 (`github.com/gofiber/fiber/v2`)
- **HTMX**: Server-rendered HTML partials with `hx-trigger`, `hx-swap`, `hx-target`
- **SSE**: Fiber v2 `SetBodyStreamWriter` + `*bufio.Writer` for streaming (see [sse.go](/apps/core/internal/web/sse.go))
- **Templates**: Embedded via `//go:embed` in `internal/web/templates/`
- **Database**: Direct `database/sql` + `lib/pq` (not sqlc for command center — raw SQL queries)
- **Temporal SDK**: `go.temporal.io/sdk` v1.39.0 for workflow dispatch and signaling

### Python AI Worker (apps/ai/)

- **SDK**: `temporalio` >= 1.11.0 for workflow/activity definitions
- **LangGraph**: `langgraph>=1.0.0` for agent state graphs
- **Prompt Optimization**: `dspy-ai>=3.1.3`
- **Structured Outputs**: `pydantic>=2.0.0` (via instructor)
- **HTTP**: `httpx>=0.28.0` (never `requests`)
- **LLM Provider**: OpenAI-compatible SDK (Groq, Azure AI Foundry, Ollama)
- **Vector DB**: `qdrant-client>=1.16.0`
- **Session Store**: `redis>=5.0.3`

### Chat Flow Architecture

1. User types `@finance` in HTMX form (command_chat.html)
2. POST to `/api/command/chat/send` → `APICommandChatSend(h)`
3. `extractMentions()` + `specialistRoutes` map → workflow type + display name
4. "🤔 Thinking..." via `tryBroadcast()` → SSE channel
5. Temporal `ExecuteWorkflow` dispatched in background goroutine
6. Python workflow completes → agent.invoke activity → Groq LLM
7. Result rendered as HTML bubble via `renderChatBubble()`
8. SSE sends `event: chat` → HTMX `sse-swap="chat"` appends to DOM

```
@mention routing (handler.go:1242-1257):
  @sarthi / @agent / @qa / @ask → QAWorkflow  → "Sarthi"
  @finance                        → FinanceWorkflow → "Finance"
  @data                           → DataWorkflow → "Data"
  @ops                            → OpsWorkflow → "Ops"
  @comms                          → CommsWorkflow → "Comms" (TBD)
  @hiring                         → HiringWorkflow → "Hiring" (TBD)
```

### 3-Tier HITL (Human-in-the-Loop)

| Tier | Description | Behavior |
|------|-------------|----------|
| **Auto** | Low-risk, high-confidence | Executes immediately, logs to agent_traces |
| **Notify** | Medium risk | Flags in dashboard timeline, no block |
| **Block** | High risk / requires approval | Writes to `planned_actions`, shows in approval queue |

- Approval action → `APICommandApprovalAction` → `SignalWorkflow(workflowID, "hitl-approval", true)`
- HITL gates block Python workflow execution until human approves

### Mission State System

- **Python AI layer** writes compiled operational state to `mission_state` table
- **Go handlers** read `mission_state` for dashboard KPIs, signals, health score
- Fields: mrr, burn_rate, runway_days, burn_alert, burn_severity, trust_score, churn_rate, error_spike, active_alerts, founder_focus
- Context budget: 800 tokens max for mission state compilation

### Goroutine Safety

- `sync.WaitGroup` tracks dispatched workflows
- Context cancellation via `c.Context().Done()` in SSE handlers
- Non-blocking `tryBroadcast()` with `select/default` on buffered channel

### Key Files

| File | Role |
|------|------|
| `/apps/core/internal/web/handler.go` | All HTTP handlers, @mention routing, SSE broadcasting |
| `/apps/core/internal/web/sse.go` | Legacy SSE handler with DB polling |
| `/apps/core/internal/temporal/client.go` | Temporal client wrapper (SignalWorkflow, ExecuteWorkflow) |
| `/apps/core/internal/workflow/stubs.go` | DiscordApprovalInput type (cleaned) |
| `/apps/core/internal/db/schema/command_center.sql` | Schema: mission_state, planned_actions, agent_traces, chat_messages |
| `/apps/core/internal/web/templates/command_center.html` | Main dashboard template (HTMX + SSE + Chart.js) |
| `/apps/core/internal/web/templates/partials/command_chat.html` | Chat panel with SSE extension |
| `/apps/core/internal/web/templates/partials/command_approvals.html` | Approval queue UI (approve/hold) |
| `/apps/core/internal/web/command_center_test.go` | Test suite (52 tests covering chat, approvals, mission state, SSE) |
| `/apps/ai/src/workflows/finance_workflow.py` | Finance specialist Temporal workflow |
| `/apps/ai/src/workflows/data_workflow.py` | Data specialist Temporal workflow |
| `/apps/ai/src/workflows/ops_workflow.py` | Ops specialist Temporal workflow |

## Architecture Evolution (2026-06-28)

**Sarthi shifted from "AI agents replace work" to "AI coordination layer":**
- Specialist agents are focused (one domain each)
- Humans own critical approvals (HITL block tier)
- Deterministic Go core handles routing, not AI decisions
- Python LLM layer for analysis & structured output only
