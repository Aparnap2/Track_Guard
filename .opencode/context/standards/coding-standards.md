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
