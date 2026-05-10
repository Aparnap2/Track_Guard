# AGENTS.md - IterateSwarm Coding Guidelines

## Project Overview

**Go + Python ChatOps platform** with Temporal orchestration and HTMX UI.

**Tech Stack:**
- **Go Core** (`apps/core/`): Go 1.24, Fiber, sqlc, Temporal SDK, HTMX
- **Python** (`apps/ai/`): Python 3.13, LangGraph, DSPy, Pydantic
- **LLM Providers**: OpenAI-compatible SDK (Azure AI Foundry, Groq, Ollama)
- **Infrastructure**: Docker (Temporal, Qdrant, PostgreSQL)

---

## V3.0 Status

| Component | Status | Notes |
|-----------|--------|-------|
| Python Tests | ✅ 38 passing | session, cofounder, guardian, slackbot tests |
| Go Build | ✅ Clean | Binary compiles successfully |
| Go HTMX Tests | ✅ 6 passing | onboarding, watchlist, llmops screens |
| HTMX Routes | ✅ 3 routes | /api/htmx/onboarding, /api/htmx/watchlist, /api/htmx/llmops |
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
- Acronyms: all caps (HTTP, URL, ID)

**Error Handling:**
- Check errors immediately: `if err != nil`
- Return errors up the call stack
- Wrap errors with context: `fmt.Errorf("context: %w", err)
- Use fiber.Error for HTTP status codes

**Struct Tags:**
- JSON tags: `json:"field_name,omitempty"`
- Database tags from sqlc generated code

**Logging:**
- Use internal/logging package
- Structured logging with key-value pairs
- Log at appropriate levels (Info, Warn, Error)

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
      api/           # HTTP handlers (Fiber + HTMX)
      agents/        # AI agents (triage, spec)
      memory/        # Qdrant client
      config/        # LLM configuration
      db/            # sqlc generated code
      database/      # Connection utilities
      temporal/      # Temporal client
      workflow/      # Temporal workflows & activities
      htmx/          # HTMX route handlers
    web/templates/   # HTML templates
    sqlc.yaml       # sqlc configuration
  ai/                # Python AI Worker
    src/             # Python source (agents, workflows, guardian)
    tests/           # Pytest test suite
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
