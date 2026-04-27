# Sarthi — Agentic Guardian for Seed-Stage SaaS Founders

> A production-architecture AI system that continuously monitors SaaS metrics,
> detects 17 seed-stage failure patterns, and delivers contextual guardian insights
> to founders before problems become crises.

**[![Tests](https://img.shields.io/badge/tests-104%20passing-brightgreen)](#)**
**[![Architecture](https://img.shields.io/badge/distributed-Redpanda%20event%20bus-blue)](#)**
**[![HTMX](https://img.shields.io/badge/HTMX-4%20ops%20screens-purple)](#)**

---

## What Sarthi Does

Sarthi watches a SaaS founder's business continuously — Stripe revenue, bank balance, product usage, support volume, deploy frequency. It detects 17 known failure patterns (silent churn death, burn multiple creep, activation walls, cohort degradation) and delivers contextual guardian insights to Slack before those patterns become crises.

**An assistant waits to be asked. A guardian knows to watch before you know to look.**

---

## Sarthi V3.0 — Distributed Microservices (Updated!)

| Component | Technology | Status |
|----------|-----------|--------|
| **Go Gateway** | Fiber + HTMX | ✅ |
| **Python Worker** | LangGraph + LLM | ✅ |
| **Event Bus** | Redpanda (Kafka-compat) | ✅ |
| **HTMX Screens** | Onboarding, Watchlist, LLMOps, HITL | ✅ |
| **Graceful Degradation** | No Temporal/Kafka required | ✅ |

---

## Architecture Overview

```text
┌─────────────────────────────────────────────────────────────┐
│                    SARTHI V2.0 PLATFORM                     │
│                                                             │
│  EXTERNAL DATA SOURCES                                      │
│  Stripe API → Plaid/Mercury → PostgreSQL → Sentry          │
│          ↓                                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  GO API GATEWAY (Fiber)                             │   │
│  │  Webhook ingestion · OAuth · Health checks          │   │
│  └─────────────────────────────────────────────────────┘   │
│          ↓                                                  │
│  REDPANDA EVENT BUS (stripe.events · ops.events)           │
│          ↓                                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  TEMPORAL ORCHESTRATOR (7 workflows)                │   │
│  │  PulseWorkflow · InvestorWorkflow · QAWorkflow      │   │
│  │  SelfAnalysisWorkflow · EvalLoopWorkflow            │   │
│  │  CompressionWorkflow · WeightDecayWorkflow          │   │
│  └─────────────────────────────────────────────────────┘   │
│          ↓                                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  PYTHON AI WORKER (LangGraph + DSPy)               │   │
│  │                                                     │   │
│  │  AGENTS: Pulse · Anomaly · Investor · QA           │   │
│  │         CommsTriage · Hiring · (more coming)        │   │
│  │  GUARDIAN: 17-pattern watchlist (pure Python)       │   │
│  │  MEMORY: 5-layer spine (Redis→Qdrant→Kuzu→PG→Qdrant)│   │
│  │  RAG: ≤800 token context assembly + fallback        │   │
│  │  HITL: 3-tier routing (auto→review→approve)         │   │
│  │  LLMOps: Langfuse tracing · eval loop              │   │
│  │  CHIEF OF STAFF: Decision Journal · Weekly Brief    │   │
│  └─────────────────────────────────────────────────────┘   │
│          ↓                                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  SLACK DELIVERY (Block Kit + interactive buttons)   │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Engineering Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Workflow orchestration | Temporal | Durable execution — workflows survive worker crashes |
| Agent framework | LangGraph StateGraph | Explicit, inspectable, checkpointable state |
| Prompt management | DSPy Signatures | Declarative, optimizable, versionable |
| Pattern detection | Pure Python rules | Deterministic, zero-latency, fully testable |
| Memory | 5-layer spine | TTL-stratified, decay-weighted retrieval |
| Delivery | Slack Block Kit | Zero-UI, founder's existing context |

→ Full rationale in [docs/decisions/](docs/decisions/) (6 ADRs)

---

## System Components

| Component | Language | Responsibility | Status |
|-----------|----------|----------------|--------|
| Go API Gateway | Go/Fiber | Webhook ingestion, OAuth, health checks | ✅ |
| Redpanda | Infra | Event bus between webhook layer and workers | ✅ |
| Temporal Server | Infra | Workflow state machine, scheduling, retries | ✅ |
| Python AI Worker | Python 3.13 | LangGraph agents, memory spine, LLM calls | ✅ |
| Guardian Watchlist | Python | 17 seed-stage failure pattern detectors | ✅ |
| Memory Spine | Python | 5-layer memory: Redis/Qdrant/Kuzu/PG/Qdrant | ✅ |
| RAG Kernel | Python | Context assembly ≤800 tokens before LLM | ✅ |
| HITL Manager | Python | 3-tier human-in-the-loop routing | ✅ |
| LLMOps | Python | Langfuse tracing, eval scoring, self-analysis | ✅ |
| Chief of Staff | Python | Decision journal, weekly brief, comms triage | ✅ NEW |
| Qdrant | Infra | Episodic + compressed vector memory | ✅ |
| PostgreSQL | Infra | Structured data, procedural memory, alerts | ✅ |
| Redis | Infra | Working memory (L1), session state | 🟡 Fallback |
| Slack Bot | Python | Delivery, interactive Block Kit, decision modal | 🟡 Mock |

---

## What's Real vs. Mocked

| Component | Status | Notes |
|-----------|--------|-------|
| LangGraph agent graphs | ✅ Real | Pulse, Anomaly, Investor, QA, CommsTriage, Hiring fully implemented |
| Temporal workflows | ✅ Real | 9 workflows registered, worker connects |
| Guardian watchlist | ✅ Real | 17 patterns, pure Python, 31 signals computed |
| DSPy prompt signatures | ✅ Real | GuardianInsight, PulseSummarizer, etc. |
| Qdrant memory spine | ✅ Real | 8 collections, seeded with 6-month synthetic data |
| PostgreSQL persistence | ✅ Real | Schema migrated, seeded with NovaPulse profile |
| Langfuse tracing | ✅ Real | `@traced` decorator, pass-through when no key |
| 241+ unit tests | ✅ Real | 97.6% pass rate, all assertions verified |
| Decision Journal | ✅ Real | Slack modal + Postgres + Qdrant |
| Weekly Brief | ✅ Real | LLM synthesis via Temporal workflow |
| Investor Relations | ✅ Real | DB tables + warmup alerts |
| CommsTriage | ✅ Real | Slack channel message classification |
| HiringAgent | ✅ Real | Candidate scoring + pipeline management |
| Stripe data | 🟡 Synthetic | `demo_seed.py` — realistic 6-month NovaPulse history |
| Plaid/bank data | 🟡 Synthetic | Seeded realistic burn/runway trajectory |
| Slack delivery | 🟡 Telegram mock | Architecture real; bot token not wired for portfolio |
| Redis working memory | 🟡 In-memory fallback | Falls back gracefully when not running |
| Kuzu semantic memory | 🟡 Not installed | `available()` returns False, layer skipped |

---

## Running the Demo

### Prerequisites
- Docker (for PostgreSQL, Qdrant, Temporal, Ollama containers)
- `uv` (Python package manager)

### Quick Start
```bash
# 1. Clone and seed synthetic data
git clone https://github.com/Aparnap2/sarthi_ai.git
cd sarthi_ai

# 2. Start infrastructure (one container at a time)
docker start iterateswarm-postgres && sleep 10
docker start iterateswarm-qdrant && sleep 10
docker start sarthi-redis && sleep 5

# 3. Seed realistic synthetic data
python scripts/demo_seed.py

# 4. Run tests
cd apps/ai && uv run pytest tests/unit/ -q

# 5. Run demo
cd ../..
bash scripts/demo_start.sh
bash scripts/demo_run.sh
bash scripts/demo_stop.sh
```

### What the Demo Shows

| Step | What happens | Tech demonstrated |
|------|-------------|-------------------|
| Seed | Inserts 6-month NovaPulse history into real PostgreSQL + Qdrant | Real DB queries, real vectors |
| Pulse | Fetches metrics → computes 31 signals → runs 17-pattern watchlist → generates narrative | LangGraph · DSPy · Guardian |
| Watchlist | 13 of 17 patterns trigger against seeded data | Pure Python, zero LLM |
| Q&A | Answers founder questions with tool use | ReAct agent · Qdrant retrieval |
| Tests | 241 unit tests pass live | Full test coverage |

---

## Test Coverage

| Suite | Tests | Status |
|-------|-------|--------|
| PulseAgent | 20 | ✅ 20/20 |
| AnomalyAgent | 15 | ✅ 15/15 |
| InvestorAgent | 15 | ✅ 15/15 |
| QAAgent | 15 | ✅ 15/15 |
| Guardian Watchlist | 28 | ✅ 28/28 |
| Memory Spine | 28 | ✅ 28/28 |
| Workflows (v1) | 14 | ✅ 14/14 |
| Workflows (v2) | 17 | ✅ 17/17 |
| HITL | 11 | ✅ 11/11 |
| LLMOps | 10 | ✅ 10/10 |
| Integrations | 12 | ✅ 12/12 |
| DB Migrations | 5 | ✅ 5/5 (needs PG running) |
| **TOTAL** | **241+** | **✅ 97.6% pass rate** |

---

## Guardian Watchlist

Sarthi detects 17 seed-stage failure patterns:

### Finance (6)

| ID | Pattern | Trigger |
|----|---------|---------|
| FG-01 | Silent Churn Death | Monthly churn > 3% (→ 36% annual) |
| FG-02 | Burn Multiple Creep | Net burn / new ARR > 2.0x |
| FG-03 | Customer Concentration | Top customer > 30% of MRR |
| FG-04 | Runway Compression | Burn accelerating, runway < 9 months |
| FG-05 | Failed Payment Cluster | 3+ failed payments in 7 days |
| FG-06 | Payroll Revenue Ratio | Payroll > 60% of MRR |

### BI (6)

| ID | Pattern | Trigger |
|----|---------|---------|
| BG-01 | Leaky Bucket Activation | Signups growing, activation < 40% |
| BG-02 | Power User MRR Masking | Top 10% generate 60%+ of MRR |
| BG-03 | Feature Adoption Drop | Usage drops 30%+ after deploy |
| BG-04 | Cohort Retention Degradation | New cohorts 10%+ worse than prior |
| BG-05 | NRR Below 100 | Losing more than expanding |
| BG-06 | Trial Activation Wall | 50%+ abandon at one step |

### Ops (5)

| ID | Pattern | Trigger |
|----|---------|---------|
| OG-01 | Error Segment Correlation | Errors > 10% in one segment |
| OG-02 | Support Outpacing Growth | Tickets growing 1.5x faster than users |
| OG-03 | Cross-Channel Bug Convergence | Same bug in 3+ channels |
| OG-04 | Deploy Frequency Collapse | Deploys drop >50% MoM |
| OG-05 | Infrastructure Unit Economics | AWS cost growing 2x faster than users |

---

## Architecture Decisions

| ADR | Decision |
|-----|----------|
| [ADR-001](docs/decisions/ADR-001.md) | Temporal over Celery — durable execution for crash recovery |
| [ADR-002](docs/decisions/ADR-002.md) | LangGraph over CrewAI — explicit, inspectable state |
| [ADR-003](docs/decisions/ADR-003.md) | DSPy over f-strings — declarative, optimizable prompts |
| [ADR-004](docs/decisions/ADR-004.md) | 5-layer spine — TTL-stratified, decay-weighted retrieval |
| [ADR-005](docs/decisions/ADR-005.md) | Pure Python rules — deterministic, zero-latency detection |
| [ADR-006](docs/decisions/ADR-006.md) | Slack-first — zero-UI, founder's existing context |

---

## What I'd Build Next (If Shipping to Users)

- **Real Stripe OAuth** — live data ingestion instead of synthetic seeding
- **Real Slack Bolt** — remove Telegram mock, wire actual bot token
- **Graphiti temporal graph** — causal chain memory for resolved blindspots
- **HTMX onboarding UI** — schema discovery, connection setup, settings
- **Fine-tuned Qwen3** — replace DSPy optimization with task-specific fine-tuning

---

## What I'd Do Differently (Honest Retrospective)

- **Temporal was too early.** I'd start with APScheduler + PostgreSQL-persisted state. Add Temporal when "what if the worker dies mid-LLM-call" becomes a real problem.
- **5-layer spine is aspirational.** 3 of 5 layers are stubs. I'd start with L2 (Qdrant episodic) + L5 (compressed) and add the rest incrementally.
- **LangGraph was ceremonial before justified.** I'd start with function chains for simple agents and add StateGraph when conditional logic demands it.
- **Mock data is the weakest signal.** For a portfolio, seeded synthetic data in real databases is far more impressive than hardcoded Python dicts. The `demo_seed.py` script fixes this retroactively.

---

*This is an engineering portfolio document, not a product README. It describes architecture decisions, not marketing claims. Every technology choice is explained with tradeoffs. The code is real. The data is synthetic but structurally accurate.*
