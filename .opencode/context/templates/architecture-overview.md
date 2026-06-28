# IterateSwarm Architecture Overview (Template)

> **Purpose**: High-level architecture summary referencing the graphify knowledge graph communities and key files. Use this as orientation for new developers or AI agents entering the codebase.

## Codebase at a Glance

```
apps/              # Source code (489 files, 6407 nodes, 8677 edges)
├── core/          # Go modular monolith (Fiber v2, HTMX, SSE, Temporal SDK)
│   ├── cmd/       # Entrypoints: server, worker
│   └── internal/  # Web handlers, workflow stubs, temporal client, DB, config
└── ai/            # Python AI worker (Temporal SDK, LangGraph, DSPy)
    └── src/       # Agents, workflows, guardian, session, tools
```

## Graphify Community Map (2026-06-14)

The knowledge graph identified 708 communities. Key clusters:

### Command & Control Layer (New — 2026-06-28)
| Community | Key Files | Description |
|-----------|-----------|-------------|
| **Mission State** | `command_center.sql`, `handler.go` | `mission_state` table, health scores, KPI rendering |
| **HITL Delivery Queue** | `handler.go`, `planned_actions` table | Approval queue, approve/hold actions, Temporal signals |
| **Go Handlers** | `handler.go` | All HTTP endpoints, @mention routing, SSE broadcast |
| **Go Temporal Activities** | `client.go`, `stubs.go` | Workflow dispatch, signal sending, health checks |

### AI Agent Layer
| Community | Key Files | Description |
|-----------|-----------|-------------|
| **Business Pipeline** | `src/agents/finance/`, `src/workflows/finance_workflow.py` | Finance anomaly detection, MRR/burn analysis |
| **BaseAgent Framework** | `src/agents/base/` | Abstract agent class, tool framework |
| **Pydantic Schemas** | `src/schemas/` | All Pydantic models for structured output |
| **Guardrails Engine** | `src/guardian/` | Relevance gate, alert gate, output validation |
| **Cofounder Agent** | `src/agents/cofounder/` | Strategic synthesis, pattern detection |
| **Startup Guardian** | `src/guardian/` | System health monitoring, anomaly detection |
| **Memory Integration** | `src/memory/` | Qdrant vector store, Redis session cache |
| **LLM Ops** | `src/config/` | API key management, model selection, rate limiting |
| **Tool Registry** | `src/agents/tools/` | ToolDef dataclass, TOOL_REGISTRY, 4 registered tools with HITL tier mapping |
| **HITL Manager** | `src/hitl/` | 3-tier routing (auto/review/approve), guardrail-aware route_extended, confidence scoring |
| **Slack Integration** | `src/integrations/slack_client.py`, `slack_buttons.py` | SocketMode WebSocket client, ACE button loop, decision modal |

### Go Core Layer
| Community | Key Files | Description |
|-----------|-----------|-------------|
| **Go Handlers** | `handler.go`, `sse.go`, `sse_hub.go` | HTTP endpoints, SSE streaming (legacy polling), SSEHub event-type fan-out |
| **SSEHub** | `sse_hub.go` | Per-subscriber channel hub with event-type filtering (`Subscribe`/`Broadcast`) |
| **Temporal Workflows** | `internal/workflow/`, `internal/temporal/` | Workflow stubs, client, activity definitions |
| **Go Database Layer** | `internal/db/`, `internal/database/` | SQL queries, connection management |
| **Config Module** | `internal/config/` | LLM provider config (Azure, Groq, Ollama) |
| **Event Bus Core** | `internal/events/` | Redpanda Kafka event publishing |
| **HTMX UI** | `internal/web/templates/` | All HTML templates, CSS, JS |

### Infrastructure
| Community | Key Files | Description |
|-----------|-----------|-------------|
| **Qdrant Memory** | `internal/memory/`, `src/memory/` | Vector storage for semantic search |
| **Redis Working Memory** | `src/session/` | Short-term session cache |
| **Redpanda Event Bus** | `internal/events/` | Kafka-compatible event streaming |

## System Architecture (ASCII)

```
┌──────────────┐     ┌─────────────────────────────────────┐
│   Browser    │────►│  Go Core (Fiber + HTMX)             │
│  (HTMX/SSE)  │     │  handler.go · sse.go · temporal/    │
└──────────────┘     └──────────┬──────────────────────────┘
                                │ ExecuteWorkflow / SignalWorkflow
                                ▼
┌──────────────────────────────────────────────────────────┐
│  Temporal Server (TRACKGUARD-MAIN-QUEUE)                  │
│  Orchestrates Go + Python tasks                           │
└──────────┬───────────────────────────────────────────────┘
           │ Activity dispatch
           ▼
┌──────────────────────────────────────────────────────────┐
│  Python AI Worker (LangGraph + DSPy + Temporal SDK)      │
│  FinanceWorkflow · DataWorkflow · OpsWorkflow            │
│  FinanceGraph  · DataGraph · OpsGraph                    │
│  → Writes: mission_state, planned_actions, agent_traces  │
└──────────────────────────────────────────────────────────┘
```

## Runtime Entrypoints

### Go Server
```bash
cd apps/core
go run cmd/server/main.go           # HTTP server on :8080
```

### Go Worker
```bash
cd apps/core
go run cmd/worker/main.go           # Temporal worker
```

### Python Worker
```bash
cd apps/ai
uv run python -m src.worker          # Temporal activity worker
```

### Infrastructure
```bash
make up    # Starts Docker: Temporal, Qdrant, PostgreSQL, Redis
make down  # Stops all services
make build # Builds Go binaries
```

## Route Map

| Route | Handler | Description |
|-------|---------|-------------|
| `GET /command` | `CommandCenter` | Main dashboard page |
| `POST /api/command/chat/send` | `APICommandChatSend` | Chat submission + Temporal dispatch in goroutine |
| `GET /api/command/chat/events` | `APICommandChatEvents` | SSE stream for chat bubbles (SSEHub, subscribes to `chat` events) |
| `GET /api/command/events` | `APICommandEvents` | SSE stream for dashboard heartbeats (legacy, no SSEHub) |
| `GET /api/command/mission/events` | `APICommandMissionEvents` | SSE stream for mission state updates (SSEHub, subscribes to `mission` events) |
| `GET /api/command/hitl/events` | `APICommandHITLEvents` | SSE stream for HITL approval signals (SSEHub, subscribes to `hitl` events) |
| `GET /api/command/session/events` | `APICommandSessionEvents` | SSE stream for session context events (SSEHub, subscribes to `session` events) |
| `GET /api/command/status` | `APICommandStatus` | Health score bar |
| `GET /api/command/kpis` | `APICommandKPIs` | KPI cards (MRR, Runway, etc.) |
| `GET /api/command/mission-state` | `APICommandMissionState` | Read mission_state for dashboard |
| `POST /api/mission-state` | `APICommandMissionStateWrite` | Write mission_state from Python AI |
| `GET /api/command/watchlist` | `APICommandWatchlist` | Watch items (FG, BG, OG) |
| `GET /api/command/timeline` | `APICommandTimeline` | Recent activity feed |
| `GET /api/command/approvals` | `APICommandApprovals` | Pending approval items |
| `POST /api/command/approvals/:id/approve` | `APICommandApprovalAction` | Approve → SignalWorkflow("hitl-approval") |
| `POST /api/command/approvals/:id/hold` | `APICommandApprovalAction` | Hold → DB update (no signal) |
| `GET /api/command/chart-data` | `APICommandChartData` | 6-week trend data (JSON) |
| `GET /api/command/agent-fleet` | `APICommandAgentFleet` | Agent fleet cards |

## Database Schema

```sql
-- Core operational tables (command_center.sql)
mission_states    -- Compiled state from Python AI (MRR, burn, health, brief, decisions)
planned_actions   -- Approval queue (actor, action_type, risk_level, workflow_id)
agent_traces      -- Activity log from Python AI (duration, tokens, cost)
chat_messages     -- Chat history (sender, mention, message)

-- Legacy tables
hitl_queue        -- Legacy HITL queue (migrating to planned_actions)
agent_outputs     -- Finance anomaly alerts, BI query results
agent_events      -- Polled SSE events for legacy dashboard
```

**Note:** `mission_state` → `mission_states` (migration 004 resolved schema drift). The MissionState dataclass (`apps/ai/src/session/mission_state.py`) now includes `prepared_brief`, `pending_decisions`, and `last_updated_by` fields.

## Quick Reference

### Adding a New Specialist Workflow

1. Create `apps/ai/src/workflows/<name>_workflow.py` — Temporal workflow definition
2. Create `apps/ai/src/agents/<name>/graph.py` — LangGraph agent
3. Add route in `handler.go` `specialistRoutes` map:
   ```go
   "@<name>": {"<Name>Workflow", "<DisplayName>"},
   ```
4. Add display name in `renderChatBubble`'s `displayName` switch
5. Register workflow in Python worker's workflow list

### Sending a Temporal Signal

```go
// In any handler:
h.temporal.SignalWorkflow(ctx, workflowID, "hitl-approval", true)
```
