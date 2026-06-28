# IterateSwarm Coding Standards

> **Purpose**: Centralized code conventions for Go core and Python AI worker.

## Go Standards (apps/core/)

### Imports

- Standard library first
- Third-party packages second
- Internal packages last with full module path (`iterateswarm-core/...`)
- Groups separated by blank lines

### Naming

| Scope | Convention | Example |
|-------|-----------|---------|
| Unexported | `camelCase` | `chatBroadcast`, `tryBroadcast` |
| Exported | `PascalCase` | `NewHandler`, `SignalWorkflow` |
| Constants | `SCREAMING_SNAKE_CASE` | `MAX_CALLS` |
| Acronyms | All caps | `HTTP`, `URL`, `ID`, `API`, `SSE`, `HITL` |

### Error Handling

- Check errors immediately: `if err != nil { ... }`
- Wrap errors with context: `fmt.Errorf("context: %w", err)`
- Use `fiber.Error` for HTTP status codes
- Log errors before returning

### Struct Tags

- JSON: `json:"field_name,omitempty"`
- Form: `form:"field_name"`
- Database tags from raw SQL scan pattern (not struct tags — uses manual Scan)

### HTTP Patterns

- **HTMX handlers**: Check `c.Get("HX-Request") == "true"` for partials vs full page
- **SSE**: Use `SetBodyStreamWriter` pattern with `*bufio.Writer`
- **Form parsing**: `c.BodyParser(&req)` with struct tags
- **Route registration**: `app.Get/Patch/Post/Delete` in `RegisterRoutes()`

### Template Rendering

```go
// Handler embeds templates with //go:embed
//go:embed templates
var templatesFS embed.FS

func Render(c *fiber.Ctx, name string, data interface{}) error {
    tmpl := template.New(name).Funcs(template.FuncMap{
        "upper": strings.ToUpper,
        "first": func(s string) string { ... },
        "displayName": func(sender string) string { ... },
    })
    // Read from embedded FS, parse, execute
}
```

### Temporal Patterns

- **Client wrapper**: `internal/temporal/client.go` wraps `client.Client`
- **ExecuteWorkflow**: `client.ExecuteWorkflow(ctx, opts, workflowName, input)`
- **SignalWorkflow**: `client.SignalWorkflow(ctx, workflowID, "", signalName, payload)`
- **Workflow input**: Always typed as `map[string]interface{}`
- **Workflow result**: `run.Get(ctx, &result)` where result is `map[string]interface{}`
- **Task queue**: `"TRACKGUARD-MAIN-QUEUE"`

### SSEHub Event Subscription Pattern

The SSEHub replaces raw `chatBroadcast` channels for new SSE endpoints. Pattern:

```go
// Subscribe with event type filter (e.g., only "chat" events)
sub := h.sseHub.Subscribe(tenantID, "chat")

// Or subscribe to multiple event types
sub := h.sseHub.Subscribe(tenantID, "mission", "hitl")

// Or subscribe to all events (no filter)
sub := h.sseHub.Subscribe(tenantID)
sub := h.sseHub.Subscribe(tenantID) // empty eventTypes = all events

// Always unsubscribe in deferred cleanup
defer h.sseHub.Unsubscribe(tenantID, sub.ID)

// Read from subscriber's channel in SetBodyStreamWriter
c.Context().SetBodyStreamWriter(func(w *bufio.Writer) {
    for {
        select {
        case msgBytes, ok := <-sub.Channel:
            if !ok { return }
            fmt.Fprintf(w, "%s", msgBytes)
            w.Flush()
        case <-done:
            return
        }
    }
})
```

- `SSEEvent.Type` determines routing — subscribers with matching `Types` filter receive the event
- Empty `Types` = receive all events for tenant
- Per-subscriber channel buffer: 64 (vs legacy `chatBroadcast` shared buffer of 100)
- `Broadcast()` uses non-blocking `select/default` per subscriber — a slow consumer drops their own events without affecting others

### Concurrency Safety

- `sync.WaitGroup` for goroutine tracking (workflow dispatch, graceful shutdown)
- Context cancellation via `c.Context().Done()` in SSE handlers
- 5-minute context timeout for workflow dispatch goroutines (`context.WithTimeout(reqCtx, 5*time.Minute)`)
- Non-blocking `tryBroadcast()` with `select { case ch <- msg: default: log }` on buffered channel (capacity 100)
- `recover()` deferred in SSE stream writers to prevent panic from closed connections
- Goroutine closures capture request context by value; always check `ctx.Done()` for streaming patterns

### Testing

```bash
go test ./...                          # All tests
go test ./internal/web/...             # Web handlers
go test ./internal/web/... -run TestChat  # Single test
```

- Tests use `httptest.NewRequest` + `app.Test(req)` for HTTP integration
- Handler struct initialized as `NewHandler(nil, nil)` for unit tests (no DB)
- HX-Request header set explicitly for HTMX partial tests

## Python Standards (apps/ai/)

### Package Management

```bash
cd apps/ai
uv sync           # Install dependencies
uv run pytest     # Run tests
```

### Code Style

- Python 3.11+ with type hints everywhere
- `ruff` for linting (imports, formatting)
- `structlog` for structured logging (never `print()`)
- Black-compatible formatting (single quotes preferred)

### Imports

```python
"""Module docstring."""
from __future__ import annotations

from datetime import timedelta
from typing import Any

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from src.agents.finance.graph import FinanceGraph
```

- Standard library first
- Third-party second
- Application imports last
- `workflow.unsafe.imports_passed_through()` for Temporal SDK compat

### Framework Standards

| Concern | Standard | Prohibited |
|---------|----------|------------|
| HTTP client | `httpx` (async) | `requests` |
| Data validation | `pydantic>=2.0.0` (strict mode) | Manual dict parsing |
| Structured output | `instructor` | Raw JSON parsing |
| LLM prompts | `dspy-ai` | String concatenation |
| Agent framework | `langgraph>=1.0.0` | Custom state machines |
| Async DB | `asyncpg` | Synchronous drivers |
| Logging | `structlog` | `print()` |
| Debugging | `ic` (icecream) | `print()` |

### Tool Creation Pattern (ToolDef)

Each tool is a standalone module in `apps/ai/src/agents/tools/` with a `tool_def` dict and an async `execute` function:

```python
"""Tool: <name> — HITL Tier: <tier>.

Description of what the tool does and when it triggers.
"""
from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)

tool_def: dict[str, Any] = {
    "name": "my_tool_name",                    # snake_case unique name
    "description": "Human-readable description",
    "hitl_tier": "review",                     # auto | review | approve | blocked
    "trigger_patterns": ["FG-05", "BG-04"],    # alert pattern IDs
}

async def execute(tenant_id: str, **kwargs) -> dict[str, Any]:
    """Execute tool logic.

    Args:
        tenant_id: Tenant identifier.
        **kwargs: Tool-specific parameters.

    Returns:
        Dict with tool result fields.
    """
    log.info("my_tool_name %s — tier=%s", tenant_id, tool_def["hitl_tier"])
    # Tool implementation
    return {"status": "done", "tenant_id": tenant_id}
```

After creating the module, register it in `__init__.py`:

```python
from . import my_tool_module

register_tool(ToolDef(**my_tool_module.tool_def, fn=my_tool_module.execute))
```

- `hitl_tier` must match one of the strings from `HITLManager.route()`: `"auto"`, `"review"`, `"approve"`, `"blocked"`
- `trigger_patterns` reference alert pattern IDs (FG-xx, BG-xx, etc.)
- Tools auto-register on import via `register_tool()`

### ACE Loop Wiring Pattern

Button interactions in Slack route through the ACE (Acknowledge-Consequence-Evaluate) loop via `slack_buttons.py`:

```python
# In button handler:
def _handle_acknowledged(alert_id: str) -> ButtonResult:
    _send_feedback_signal(alert_id, "acknowledged", 1.0)  # +1.0 trust signal
    return ButtonResult(success=True, action="acknowledge", ...)

# Signal wiring (skip in test):
def _send_feedback_signal(alert_id, response_type, score):
    if "pytest" in sys.modules:  # skip during unit tests
        return
    from src.agents.cofounder.reflector import score_from_button
    score_from_button(alert_id, response_type, score)
    from src.agents.cofounder.curator import update_strategy_confidence
    update_strategy_confidence(tenant_id, domain, response_type, score)
```

- Button actions: `acknowledge` (+1.0), `dispute` (-1.0), `show_breakdown`, `log_decision`
- ACE loop: Button click → Reflector scores → Curator updates strategy confidence
- Test guard: `if "pytest" in sys.modules` prevents async blocking in test envs

### Temporal Workflow Pattern

```python
@workflow.defn
class FinanceWorkflow:
    @workflow.run
    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        question = input_data.get("question", "")
        tenant_id = input_data.get("tenant_id", "default")

        agent = FinanceGraph()
        result = await workflow.execute_activity(
            agent.invoke,
            args=[{"question": question, "tenant_id": tenant_id}],
            start_to_close_timeout=timedelta(seconds=120),
        )

        return {"ok": True, "qa_result": result, "specialist_type": "finance"}
```

- Workflow definitions use `@workflow.defn`
- Run method is `async def run(self, input_data) -> dict`
- Activities use `workflow.execute_activity()` with timeout
- Activities pass through LangGraph agent graphs for execution

### Testing

```bash
cd apps/ai
uv run pytest tests/ -v                               # All Python tests (319+)
uv run pytest tests/test_session.py -v                # Session tests
uv run pytest tests/test_guardian.py -v               # Guardian tests
uv run pytest tests/ --cov=src --cov-report=term-missing  # Coverage

cd apps/core
go test ./internal/web/... -v                         # Go web handler tests (52)
```

- `pytest` with `pytest-asyncio` for async tests
- `respx` for mocking `httpx` calls (no real API calls in unit tests)
- `polyfactory` for Pydantic model fixtures
- Go web handlers: `NewHandler(nil, nil)` for unit tests (no DB/Temporal)
- SSE endpoints: `app.Test(req)` with proper `HX-Request` headers

## E2E Testing

- Playwright for browser-level HTMX interactions
- Tests live in `tests/e2e/` directory
- Verify SSE connection, form submission, bubble rendering

## Git Conventions

- **Branch**: `feature/description` — never commit to `main`
- **Commits**: Conventional Commits (`feat:`, `fix:`, `refactor:`)
- **PR**: Open draft PR, address CodeRabbit comments, merge

## Formatters & Linters

| Language | Tool | Config Location |
|----------|------|-----------------|
| Go | `go fmt` + `goimports` | Built-in |
| Python | `ruff` | `pyproject.toml` |
| SQL | `sqlc` format | `sqlc.yaml` |
| Protobuf | `buf generate` | `proto/` + `buf.gen.yaml` |

## Key Dependencies

### Go (go.mod)
- `github.com/gofiber/fiber/v2` v2.52.11 — HTTP framework
- `go.temporal.io/sdk` v1.39.0 — Temporal workflow client
- `github.com/lib/pq` v1.11.2 — PostgreSQL driver
- `github.com/jackc/pgx/v5` v5.8.0 — PostgreSQL driver (alternate)
- `github.com/stretchr/testify` v1.11.1 — Test assertions

### Python (pyproject.toml)
- `temporalio` >= 1.11.0 — Temporal SDK
- `langgraph` >= 1.0.0 — Agent graph framework
- `langchain` >= 0.3.0 — LLM framework
- `pydantic` >= 2.0.0 — Data validation
- `httpx` >= 0.28.0 — HTTP client
- `structlog` >= 25.0.0 — Structured logging
- `dspy-ai` >= 3.1.3 — Prompt optimization
- `qdrant-client` >= 1.16.0 — Vector database
