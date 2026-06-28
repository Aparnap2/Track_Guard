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

> **Architecture decisions documented in:** [ADR-001: Sarthi v4.0 Architecture Evolution](../adr/001-sarthi-v4-architecture-evolution.md) (10 decisions, incl. SSEHub, ToolRegistry, Slack SocketMode)

## Key Design Decisions

### Go Modular Monolith (apps/core/)

- **Framework**: Fiber v2 (`github.com/gofiber/fiber/v2`)
- **HTMX**: Server-rendered HTML partials with `hx-trigger`, `hx-swap`, `hx-target`
- **SSE**: Fiber v2 `SetBodyStreamWriter` + `*bufio.Writer` for streaming
  - **SSEHub** (`sse_hub.go`): Event-type filtered fan-out hub with per-subscriber channels
  - `Subscribe(tenantID, eventTypes...)` creates typed subscriptions
  - `Broadcast(tenantID, SSEEvent)` delivers only to matching subscribers (non-blocking)
  - Backward-compatible: `tryBroadcast()` pushes to both legacy `chatBroadcast` channel and SSEHub
  - Legacy polling-based SSE in [sse.go](/apps/core/internal/web/sse.go) (deprecated for new endpoints)
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

- **Python AI layer** writes compiled operational state to `mission_states` table (migration 004 reconciled schema drift `mission_state` → `mission_states`)
- **Go handlers** read `mission_states` for dashboard KPIs, signals, health score
- Core fields: mrr, burn_rate, runway_days, burn_alert, burn_severity, trust_score, churn_rate, error_spike, active_alerts, founder_focus
- **New cognitive offloading fields (2026-06-28):**
  - `prepared_brief` — LLM-generated brief prepopulated for founder context before a decision
  - `pending_decisions` — JSONB array of open decisions awaiting founder action
  - `last_updated_by` — Which agent/specialist last wrote to MissionState (traceability)
- Context budget: 800 tokens max for mission state compilation
- Dataclass in: `apps/ai/src/session/mission_state.py`
- Table references: `mission_states` (plural, not `mission_state`)

### Tool Calling Surface (ToolRegistry + HITL Tier Mapping)

New in 2026-06-28. Agent actions are defined as standalone `ToolDef` entries in a global `TOOL_REGISTRY` and wired to the HITL manager for automatic tier assignment.

```
ToolDef {
    name: str               # snake_case unique tool name
    description: str        # human-readable
    hitl_tier: str          # "auto" | "review" | "approve" | "blocked"
    fn: Callable            # async execute function
    trigger_patterns: list  # alert patterns that suggest this tool
}
```

**4 registered tools:**

| Tool | Tier | Pattern | Description |
|------|------|---------|-------------|
| `pause_failed_payment_retry` | review | FG-05 | Pause Stripe retry on 3+ failed payments |
| `draft_investor_update` | approve | schedule/manual | Draft investor email for approval |
| `schedule_customer_checkin` | auto | FG-03, BG-04 | Auto-schedule at-risk customer reminder |
| `flag_churn_risk_customer` | auto | BG-06, BG-04 | Flag segment for churn monitoring |

- Tools auto-register via `register_tool(ToolDef(...))` on module import
- `get_tools_for_tier(tier)` returns tools matching a routing decision
- `get_tools_for_patterns(pattern_ids)` returns tools matching triggered alerts
- Location: `apps/ai/src/agents/tools/__init__.py` + 4 tool modules

### Slack Consolidation — SocketMode + ACE Loop

New in 2026-06-28. The `SlackClient` was extended with `SocketModeClient` (WebSocket-based event ingestion) to handle interactive button payloads without a public HTTP endpoint.

- **SocketMode**: WebSocket connection via `slack_sdk.socket_mode.SocketModeClient` — no Bolt framework
- **Button routing** (`slack_buttons.py`): `acknowledge`, `dispute`, `show_breakdown`, `log_decision`
- **ACE loop**: Button clicks → `_send_feedback_signal()` → `score_from_button()` (Reflector) + `update_strategy_confidence()` (Curator)
- **Decision modal**: `open_decision_modal()` captures structured decision data (decision, alternatives, reasoning)
- Location: `apps/ai/src/integrations/slack_client.py`, `apps/ai/src/integrations/slack_buttons.py`

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
| `/apps/core/internal/web/command_center_test.go` | Test suite (19+ command center tests, part of 74+ web tests) |
| `/apps/core/internal/web/sse_hub.go` | SSEHub fan-out hub with event-type filtering (Subscribe/Broadcast) |
| `/apps/ai/src/workflows/finance_workflow.py` | Finance specialist Temporal workflow |
| `/apps/ai/src/workflows/data_workflow.py` | Data specialist Temporal workflow |
| `/apps/ai/src/workflows/ops_workflow.py` | Ops specialist Temporal workflow |
| `/apps/ai/src/agents/tools/__init__.py` | ToolRegistry with ToolDef dataclass, auto-registration, tier queries |
| `/apps/ai/src/agents/tools/pause_payment_retry.py` | Tool: Pause Stripe retry (tier: review) |
| `/apps/ai/src/agents/tools/draft_investor_update.py` | Tool: Draft investor email (tier: approve) |
| `/apps/ai/src/agents/tools/schedule_customer_checkin.py` | Tool: Schedule at-risk checkin (tier: auto) |
| `/apps/ai/src/agents/tools/flag_churn_risk.py` | Tool: Flag churn risk segment (tier: auto) |
| `/apps/ai/src/integrations/slack_client.py` | Slack WebClient + SocketModeClient for interactive messages |
| `/apps/ai/src/integrations/slack_buttons.py` | ACE button routing (acknowledge, dispute, breakdown, log_decision) |
| `/apps/ai/src/hitl/manager.py` | HITLManager with route_extended for guardrail-aware tier routing |
| `/apps/ai/src/hitl/confidence.py` | Confidence scoring (pattern_seen_before, data_quality, volatility) |
| `/apps/ai/src/hitl/approval_queue.py` | Approval request/response with Slack notification |

## Architecture Evolution (2026-06-28)

**Sarthi shifted from "AI agents replace work" to "AI coordination layer":**
- Specialist agents are focused (one domain each)
- Humans own critical approvals (HITL block tier)
- Deterministic Go core handles routing, not AI decisions
- Python LLM layer for analysis & structured output only
