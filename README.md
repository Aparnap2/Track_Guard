# Sarthi — Digital Mantriparishad for Seed-Stage Founders

> An Operational Decision Intelligence system architected on Kautilyan statecraft principles.
> Not a chatbot — a trusted multi-agent council that observes, analyzes, decides, and learns.

**[![Tests](https://img.shields.io/badge/tests-407%20passing-brightgreen)](#)**
**[![Architecture](https://img.shields.io/badge/architecture-Kautilyan%20council-blue)](#)**
**[![Trust](https://img.shields.io/badge/trust-Profiled%20%2B%20Gated-orange)](#)**

---

## The Architecture: A Digital Mantriparishad

Sarthi is modeled on the **Saptanga** (seven limbs of state) and **18 Tirthas** (chief officers) from Kautilya's Arthashastra. Each agent is a specialized minister with bounded authority, durable memory, and explicit trust governance.

```text
                    ┌──────────────────────┐
                    │     SWAMI (Founder)   │
                    │  Final authority for  │
                    │  irreversible decisions│
                    └──────┬───────────────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
     ┌────────▼──┐  ┌─────▼──────┐  ┌──▼─────────┐
     │ PRATIHARA │  │  AMATYA    │  │  NYAYADISH │
     │ Gatekeeper│  │  Council   │  │  Arbitrator│
     │ schema +  │  │  Mantri-   │  │  agent     │
     │ trust +   │  │  parishad  │  │  conflicts │
     │ dedup     │  │  synthesis │  │            │
     └───────────┘  └─────┬──────┘  └────────────┘
                          │
         ┌────────────────┼────────────────┐
         │                │                │
  ┌──────▼─────┐  ┌──────▼──────┐  ┌──────▼──────┐
  │  SAMAHARTA │  │    SUTA    │  │  NAGARIKA   │
  │  Finance   │  │  BI Analyst│  │  Ops Watch  │
  │  Guardian  │  │  (leading  │  │  (operational│
  │  (revenue) │  │  indicators)│  │  heartbeat) │
  └──────┬─────┘  └──────┬──────┘  └──────┬──────┘
         │                │                │
         └────────────────┼────────────────┘
                          │
              ┌───────────▼───────────┐
              │      CHARAKA         │
              │  Wandering Spy —     │
              │  cross-domain anomaly│
              │  inconsistency check │
              └──────────────────────┘
                          │
              ┌───────────▼───────────┐
              │     KOSHA / DANDA     │
              │  Treasury + Army      │
              │  MissionState + Alert │
              │  Dispatch             │
              └──────────────────────┘
                          │
              ┌───────────▼───────────┐
              │        MITRA         │
              │  Graphiti temporal   │
              │  knowledge graph —   │
              │  institutional memory│
              └──────────────────────┘
```

---

## The 18 Tirthas: Kautilya's Officer Corps Mapped to Code

| # | Tirtha | Function | Sarthi Component | File |
|---|--------|----------|-----------------|------|
| 1 | **Mantri** | Chief Minister — strategic deliberation | `CorrelationAgent` + `Mantriparishad` | `agents/cofounder/correlation.py`, `joint_council.py` |
| 2 | **Purohita** | Ethical Counsel — trust governance | `TrustBattery` — degraded gate | `services/trust_battery.py` |
| 3 | **Samaharta** | Collector-General — revenue aggregation | `FinanceGuardian` | `agents/finance/graph.py` |
| 4 | **Sannidhata** | Treasury Keeper — guard financial truth | `MissionState` in PostgreSQL | `session/mission_state.py` |
| 5 | **Senapati** | Commander — execute, don't deliberate | Alert dispatch engine | `services/alert_gate.py` (dispatch) |
| 6 | **Durgapala** | Fort Governor — watch for internal breach | Rate limiter + circuit breaker pattern | `session/relevance_gate.py` |
| 7 | **Nagarika** | City Superintendent — ops heartbeat | `OpsWatch` guardian | `agents/ops/graph.py` |
| 8 | **Pratihara** | Gatekeeper — control access to founder | `AlertGate` — 4-stage quality gate | `services/alert_gate.py` |
| 9 | **Suta** | Charioteer — leading indicators | `BIAnalyst` guardian | `agents/bi/graph.py` |
| 10 | **Gopa** | Village Accountant — raw data collection | Data ingestion pipeline | `memory/qdrant_ops.py` |
| 11 | **Sthanika** | District Officer — mid-tier signal processor | Watchlist pattern engine | `guardian/watchlist.py` |
| 12 | **Yukta** | Secretary — perfect recording, no deciding | `SessionMemoryWriter` + Langfuse traces | `session/memory_integration.py` |
| 13 | **Akshapataladhyaksha** | Accountant-General — consolidated view | Dashboard / MissionState aggregator | `session/mission_state.py` |
| 14 | **Nyayadish** | Chief Justice — arbitrate agent conflicts | `Nyayadish` — agent conflict arbiter | `agents/cofounder/arbiter.py` |
| 15 | **Rajuka** | Reward/Punishment — autonomous demotion | Trust Battery score decay | `services/trust_battery.py` |
| 16 | **Dharmamahamatras** | Welfare Officers — founder override | `founder_disputed` ACE loop | `session/memory_integration.py` |
| 17 | **Charaka** | Wandering Spy — cross-domain anomaly | `Charaka` — inconsistency detector | `agents/anomaly/graph.py` |
| 18 | **Yuvaraja** | Crown Prince — institutional memory | Graphiti temporal knowledge graph | `memory/semantic.py` |

---

## Core Components

### Trust Battery (Purohita)
Every agent has a dynamic trust profile with score (0.0–1.0), route priority, degraded mode, and full event audit history. Degraded agents (trust < 0.4) are hard-blocked at the relevance gate — they cannot fire until trust is restored.

### Session Layer (Mantriparishad)
The `MissionState` is the single source of ground truth — shared context that every guardian reads and writes. The `relevance_gate` determines which agents should respond using keyword triggers + active alerts + Trust Battery.

### Joint Alert Council (Mantriparishad)
When 2+ guardians fire in the same session, the council synthesizes them into one alert with unified root cause, cross-domain severity, and a single recommended action. Prevents alert fatigue.

### Alert Quality Gate (Pratihara)
Every alert passes through 4 stages before reaching the founder:
1. **Schema validation** — required fields, valid types
2. **Trust check** — agent not degraded
3. **Dedup check** — same alert not sent in last 60 minutes
4. **Tone filter** — basic text quality

### Cross-Domain Spy (Charaka)
Roams across all MissionState fields looking for inconsistencies: burn alerts without operational symptoms, revenue growth with cash burn, short runways with misplaced founder focus.

### Agent Arbiter (Nyayadish)
Resolves contradictions between guardians — severity mismatches (critical vs. info) and signal contradictions. Highest severity wins; majority override available.

---

## What Sarthi Answers

Every alert or recommendation answers four questions:

| Question | How |
|----------|-----|
| **What happened?** | Guardian detects metric deviation |
| **Why did it happen?** | Narrative layer explains root cause |
| **What if nothing changes?** | (Coming) Predictive Guardian — runway projection, churn probability |
| **What should be done?** | Concrete recommended action with deadline |

---

## One-Week Incident Lifecycle

```text
T+0   → Raw data arrives (webhook / sync)
T+3m  → Guardian cycle fires (detect → reason → decide)
T+5m  → Alert passes Pratihara gate (schema → trust → dedup → tone)
T+6m  → If 2+ guardians: Mantriparishad synthesizes
T+7m  → Charaka checks for cross-domain inconsistencies
T+10m → Founder receives alert on Slack with recommendation
T+12m → Founder acknowledges / disputes via Slack button
T+15m → Trust score updated, event logged to Graphiti
T+48h → Follow-up check: was action taken? Outcome measured?
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **LLM** | OpenRouter (nemotron-3-super-120b via API) |
| **Embeddings** | OpenRouter (llama-nemotron-embed-vl-1b, 2048-dim) |
| **Semantic Memory** | Graphiti + Neo4j 5.26 |
| **Vector Store** | Qdrant (episodic + compressed) |
| **Relational DB** | PostgreSQL (MissionState, trust events, sessions) |
| **Cache** | Redis (working memory, session TTL) |
| **Tracing** | Langfuse v4 (@observe) |
| **Language** | Python 3.13, Go 1.24 |
| **Config** | Env-only via pydantic-settings — zero hardcoded secrets |

---

## Test Coverage (407+ Passing)

| Suite | Tests | Status |
|-------|-------|--------|
| Trust Battery | 19 | ✅ |
| Session Layer | 35 | ✅ |
| Co-founder Agent | 20 | ✅ |
| Correlation + Avoidance | 14 | ✅ |
| Guardian Watchlist | 69 | ✅ |
| Finance Guardian | 25 | ✅ |
| Memory Spine (Graphiti) | 26 | ✅ |
| LLMOps | 15 | ✅ |
| Workflows | 31 | ✅ |
| HITL | 11 | ✅ |
| Integrations | 16 | ✅ |
| Embeddings + Qdrant | 26 | ✅ |
| All Others | 100+ | ✅ |

---

## Quick Start

```bash
# Start infrastructure
docker start sarthi-postgres sarthi-neo4j sarthi-qdrant sarthi-redis

# Run tests
cd apps/ai && uv run pytest tests/unit/ -q

# Run worker
cd apps/ai && uv run python -m src.worker
```

---

## Development Principles

1. **Decision latency** — every feature must shorten the time between signal and action
2. **Exception quality** — high trust beats high volume; reduce false positives
3. **Founder cognition** — fewer, sharper, more actionable messages
4. **Trust gradually** — copilot → workflow assistant → semi-autonomous → autonomous
5. **No hardcoded secrets** — env-only configuration, centralized in `config/database.py`
