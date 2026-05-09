# SARTHI V3.0 — PRODUCT REQUIREMENTS DOCUMENT

```
Version:  3.0
Date:     April 26, 2026
Status:   Approved for Build
ICP:      Solo technical SaaS founder, seed stage, 6–18 months to Series A
Stack:    Python · Go · LangGraph · Pydantic AI · APScheduler · Graphiti · Neo4j
          Qdrant · PostgreSQL · Redis · Slack · Azure (Free Tier)
```

---

## 1. Product Truth

Sarthi is a **guardian**, not an assistant.

Every tool ever built for founders operates in the known-knowns quadrant — they answer questions the founder already knows to ask. A first-time solo technical founder doesn't know what they don't know. They don't know that 3% monthly churn is fatal at Series A. They don't know that their AWS costs growing faster than their users is a structural unit economics problem. They don't know that inconsistent investor updates signal operational discipline problems to the next investor.

**An assistant waits to be asked. A guardian knows to watch before you know to look.**

Sarthi watches continuously, detects patterns from a curated watchlist of seed-stage failure modes, and surfaces insights the founder could not have surfaced themselves — before those patterns become crises.

**Core tagline:** *"First-time founders don't know what they don't know. Sarthi does."*

---

## 2. ICP — Locked

> **Sarthi V1 is for the solo technical founder building a SaaS product on Stripe + Postgres, at seed stage, who is 6–18 months from their first institutional raise — and who doesn't yet know what's about to go wrong.**

| Qualifier            | Why It Matters                                               |
| -------------------- | ------------------------------------------------------------ |
| Solo                 | No delegation buffer — every alert hits the decision-maker directly |
| Technical            | Can self-serve onboarding; no CS layer required              |
| SaaS                 | Instrumentation already exists (Stripe, DB, Sentry)          |
| Seed stage           | Failure patterns are well-documented and watchlist-able      |
| 6–18 months to raise | Urgency horizons are calculable and meaningful               |

**Explicitly out of V1:**
- D2C / ecommerce founders
- Agency / services founders
- Non-technical SaaS founders
- Mobile-first app founders (Firebase/Amplitude schema variance)
- Pre-product founders (nothing to watch)
- Multi-founder teams > 2

---

## 3. V2.0 → V3.0 Delta

**V2.0 complete:**
- 4 agents: Pulse, Anomaly, Investor, QA
- 3 Temporal workflows + 5 activities (replaced by APScheduler in V3)
- Qdrant memory: 3 collections (768-dim)
- DSPy prompts: examples + signatures
- Integrations: Stripe, Plaid, ProductDB, Slack
- Guardian watchlist: 16 seed-stage failure patterns
- 5-layer memory spine (Redis → Qdrant → Kuzu → PG → Qdrant compressed)
- RAG kernel (≤800 token context assembly)
- 3-tier HITL system
- LLMOps: Langfuse tracing + weekly eval loop
- 119+ tests passing

**V3.0 adds:**

### Architecture Changes
- **Temporal → APScheduler** (running, persisted to Postgres, 10 jobs verified)
- **Kuzu → Neo4j + Graphiti** (temporal knowledge graph with episodic memory)
- **Pydantic AI** wraps every LLM output (enforced output contract, auto-retry)
- **HTMX internal ops dashboard** (alert queue, watchlist status, eval scores)
- **Azure Free Tier** deployment (14 services, ₹0/month infra)

### Interaction Model Changes (ACE — Agentic Context Engineering)
- **Co-founder Agent** (manager): session manager, triage, Generator→Reflector→Curator loop
- **Employee Agents ×3** (workers): Finance Guardian, BI Analyst, Ops Watch as ACE Generators
- **#sarthi Slack channel** as the persistent shared session (ACE session layer)
- **MissionState** shared context object — written and read by all agents in real time
- **Relevance gate** (pure code): agents self-activate when their domain is triggered
- **ACE self-improvement loop**: Generator → Reflector → Curator per agent run

### Memory Architecture Changes
- **Graphiti** handles L3 semantic memory (replaces Kuzu): temporal edges, entity resolution, contradiction handling, bi-temporal queries
- **Graphiti playbook** stores evolving founder-specific strategies per domain
- **Graphiti entities**: Decision, Alert, Investor, Customer, Strategy, Intent, Agent, Session

### Token Efficiency (Thin LLM, Fat Deterministic Core)
- Max 3 LLM calls per workflow (down from 8–12)
- LLM used only for: anomaly judgment, narrative generation, NL intent parsing
- All fetching, computing, filtering, routing, scheduling: pure Python/SQL
- Estimated 83% token reduction (~$0.18/month vs ~$1.08/month for 3 tenants)

---

## 4. Data Contract — Fixed for V1

**Required (minimum viable guardian):**
```
Stripe      → MRR, churn events, new customers, failed payments,
              plan distribution, customer concentration
PostgreSQL  → users, sessions/events, feature_usage, cohorts
              (founder-supplied, read-only)
```

**Optional (upgrades guardian quality):**
```
Plaid / Mercury  → bank balance, burn calculation
Sentry           → error rate, user segment correlation
IterateSwarm     → classified feedback, severity distribution
```

**Out of V1 data contract (closed):**
Firebase, Amplitude, Mixpanel, Segment, Intercom events, HubSpot, QuickBooks, MySQL, anything requiring custom schema mapping.

---

## 5. The Guardian Watchlist — 16 Patterns (Unchanged from V2)

### Finance Guardian
| ID    | Pattern                           | Trigger                                 |
| ----- | --------------------------------- | --------------------------------------- |
| FG-01 | `silent_churn_death`              | Monthly churn > 3% (→ 36% annual)       |
| FG-02 | `burn_multiple_creep`             | Net burn / new ARR > 2.0x               |
| FG-03 | `customer_concentration_risk`     | Top customer > 30% of MRR               |
| FG-04 | `runway_compression_acceleration` | Burn growing faster than runway shrinks |
| FG-05 | `failed_payment_cluster`          | 3+ failed payments in 7 days            |
| FG-06 | `payroll_revenue_ratio_breach`    | Payroll > 60% of revenue                |

### BI Guardian
| ID    | Pattern                             | Trigger                                         |
| ----- | ----------------------------------- | ----------------------------------------------- |
| BG-01 | `leaky_bucket_activation`           | Signups growing, activation flat or falling     |
| BG-02 | `power_user_mrr_masking`            | Top 10% users hiding declining avg MRR/customer |
| BG-03 | `feature_adoption_post_deploy_drop` | Feature usage drops after deploy                |
| BG-04 | `cohort_retention_degradation`      | New cohorts retaining 10%+ worse than prior     |
| BG-05 | `nrr_below_100_seed`                | NRR < 100% (losing more than expanding)         |
| BG-06 | `trial_activation_wall`             | Users abandoning at same step repeatedly        |

### Ops Guardian
| ID    | Pattern                                    | Trigger                                   |
| ----- | ------------------------------------------ | ----------------------------------------- |
| OG-01 | `error_rate_user_segment_correlation`      | Errors concentrated in one user segment   |
| OG-02 | `support_volume_outpacing_growth`          | Support tickets growing faster than users |
| OG-03 | `cross_channel_bug_convergence`            | Same bug in 3+ channels simultaneously    |
| OG-04 | `deploy_frequency_collapse`                | Deploy frequency drops >50% MoM           |
| OG-05 | `infrastructure_unit_economics_divergence` | AWS cost growth > 2x user growth          |

---

## 6. Guardian Message Protocol (Unchanged)

Every alert must follow this structure. No exceptions.

```
1. PATTERN NAME (not metric name)
2. The number — injected, never LLM-generated
3. What it implies at scale / at Series A
4. What the founder doesn't know yet
5. Urgency horizon (specific to 6–18 month raise timeline)
6. What typically happens to founders who miss this
7. ONE concrete action this week

Max 200 words. Starts with pattern. Ends with action.
Sounds like a trusted colleague who has seen this before.
Never sounds like a notification. Never starts with a number.
```

---

## 7. V3.0 Interaction Model — ACE Session Layer

### The #sarthi Channel as Shared Session

One Slack channel: `#sarthi`. All agents and the founder share this session.
Every message the founder types is context every agent reads.
Agents self-activate when their domain keyword is triggered — not on fixed schedule alone.

```
#sarthi
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Founder [9:02 AM]
we're thinking of dropping the ₹3,000 plan entirely

  ┌─ Sarthi · Finance [9:02 AM] ─────────────────────┐
  │ That plan has 3 of your 11 active customers.      │
  │ Combined MRR: ₹9,000. Churn risk if dropped:      │
  │ medium — 1 of 3 is 45d from renewal.             │
  │                                                   │
  │ [📊 Show breakdown]  [📌 Log decision]            │
  └───────────────────────────────────────────────────┘

  ┌─ Sarthi · Ops [9:02 AM] ──────────────────────────┐
  │ Those 3 customers filed 0 support tickets and use  │
  │ 2 of 8 features. Low engagement. Low ops impact.  │
  └────────────────────────────────────────────────────┘

Founder [9:03 AM]
ok log it. dropping ₹3,000 plan end of May

  ┌─ Sarthi [9:03 AM] ────────────────────────────────┐
  │ 📌 Decision logged                                 │
  │ "Drop ₹3,000 plan — effective end of May"         │
  │ Domain: Pricing · Reversible ✓                    │
  │                                                   │
  │ I'll track the 3 affected customers and alert you  │
  │ 2 weeks before their renewals.                    │
  └────────────────────────────────────────────────────┘
```

### Agent Persona Map

| Agent | Slack Name | Role | Voice |
|---|---|---|---|
| Co-founder Agent | `Sarthi` | Manager: routes, synthesises, escalates | Concise, decisive |
| Finance Guardian | `Sarthi · Finance` | Employee: finance domain | Numbers-first, CFO tone |
| BI Analyst | `Sarthi · Data` | Employee: BI + NL QA domain | Precise, query-driven |
| Ops Watch | `Sarthi · Ops` | Employee: ops + product domain | Pattern-focused |

### Co-founder Agent Authority (Confirmed: Option C)
- **Low severity signals** (info, warning with confidence >0.85): Co-founder decides, surfaces one synthesised message
- **Critical signals or confidence <0.60**: Always escalates conflict to founder with [options] buttons
- **Investor update drafts**: Always requires explicit founder approval (Tier 3 HITL)

### Relevance Gate (Pure Code — Zero LLM)
```python
DOMAIN_KEYWORDS = {
    "finance":  ["burn", "runway", "revenue", "MRR", "budget", "cost",
                 "raise", "invest", "plan", "price", "₹", "$", "spend"],
    "ops":      ["support", "ticket", "bug", "error", "churn", "usage",
                 "feature", "feedback", "sentry", "user", "product"],
    "bi":       ["metric", "DAU", "MAU", "retention", "cohort", "growth",
                 "data", "dashboard", "report", "trend", "last month"],
}
# Agent responds only if: keyword_hit OR (active_alert AND question)
# Never responds to every message — that is noise
```

---

## 8. ACE Self-Improvement Loop (Stanford ACE Framework)

Each employee agent implements the Generator → Reflector → Curator loop.

### Generator
Each employee agent (Finance, BI, Ops) executes tasks using the current Graphiti playbook for their domain — evolving founder-specific strategies, not static prompts.

### Reflector
After the founder responds to an alert (acknowledged / disputed / ignored / acted-on), the Co-founder Agent runs the Reflector — reading founder's Slack response as feedback signal:

```
acknowledged  → +1.0
acted_on      → +1.5
ignored 30min → -0.5
disputed      → -1.0
dismissed     → -1.5
```

### Curator
Updates the Graphiti playbook with structured delta — not a full rewrite, incremental confidence updates per strategy node. This is the mechanism that causes Sarthi to improve threshold tuning over time.

---

## 9. Thin LLM, Fat Deterministic Core

Every workflow follows the 3-phase pattern:

**Phase 1 — DATA ASSEMBLY (zero LLM tokens)**
Pure Python. Fetch everything. Compute everything. Output: typed dataclass.

**Phase 2 — COGNITIVE DECISION (1 small LLM call)**
Input: typed dataclass — numbers only, no prose.
Output: Pydantic AI model `{ should_alert: bool, severity: str, primary_signal: str }`
~150 tokens in, ~40 tokens out.

**Phase 3 — NARRATIVE GENERATION (1 LLM call, bounded)**
Input: Pydantic decision + raw numbers.
Output: capped at 200 words, hard stop via max_tokens.
Never re-fetches data. Never reasons about data. Just writes.

**Boundary test before every LLM call:**
1. Could an if/elif answer this? → Use code
2. Could a SQL query answer this? → Use SQL
  If both answers are no → LLM's job.



the llm takes lot of token , even in predicted , systematic ( pydantic ) workflow based vertical agentic ai system, isnt there a way just to use llm agent for cognitive decision ( dynamic) and dependent more on sratic code

Yes — and this pattern now has a proper name. Garry Tan (YC CEO) published "**Thin Harness, Fat Skills**" in April 2026 and it describes exactly what you are asking for. The architecture principle: push intelligence as high as possible into skills (markdown + LLM), push execution as far down as possible into deterministic code, and keep the interface between them thin (~200 lines). Sarthi should be rebuilt around this.

------

## The Core Reframe

Right now Sarthi probably routes everything through the LLM — fetching data, formatting numbers, choosing what to alert, writing the message. That is the expensive mistake. The LLM should touch exactly three things: **anomaly judgment** (is this number bad enough to act on?), **narrative generation** (write 100 words explaining what it means), and **intent parsing** (what is the founder asking for in natural language?). Everything else — fetching, computing, filtering, routing, scheduling, formatting — is static Python.

------

## What Stays Code vs. What Gets LLM

| Task                                              | Who Does It                        | Why                                                        |
| :------------------------------------------------ | :--------------------------------- | :--------------------------------------------------------- |
| Fetch Stripe MRR, burn, runway                    | `fetchfinancialdata()` Python      | Deterministic — same input, same output                    |
| Compute days overdue for investor                 | SQL query                          | Pure arithmetic                                            |
| Detect anomaly: runway < 180 days                 | `if runway < 180` Python rule      | No ambiguity — threshold is a config value                 |
| Detect anomaly: MRR drop > 10%                    | `if mrrchange < -0.10` Python rule | Same                                                       |
| **Decide: is this worth alerting given context?** | **LLM**                            | Needs judgment — was last month also bad? Is this a trend? |
| Format Slack Block Kit payload                    | Python dict constructor            | Fully deterministic                                        |
| **Write the 100-word alert narrative**            | **LLM**                            | Needs language, tone, founder-specific framing             |
| Route to correct agent                            | Python if/elif                     | Deterministic — topic keyword map                          |
| **Parse: "what was our churn last month?"**       | **LLM → structured output**        | Ambiguous natural language                                 |
| Generate SQL from parsed intent                   | Templated SQL + injected params    | Deterministic after parsing                                |
| Validate SQL (no DROP/INSERT)                     | Regex + allowlist                  | Pure code                                                  |
| Write result to Qdrant                            | Python Qdrant client               | Deterministic                                              |
| APScheduler scheduling                            | Python cron                        | Pure code                                                  |
| Weekly brief assembly                             | Python dict merge                  | Data assembly only                                         |
| **Write the brief narrative**                     | **LLM**                            | Synthesis across data needs intelligence                   |

------

## The Refactored Pattern for Each Agent

Every agent becomes a 3-phase structure:

```
textPhase 1: DATA ASSEMBLY (zero LLM tokens)
  All Python. Fetch everything. Compute everything.
  Output: a fully-populated typed dict.

Phase 2: COGNITIVE DECISION (1 small LLM call)
  Input: the typed dict — numbers only, no prose.
  Output: Pydantic model: { should_alert: bool, reason: str, severity: str }
  Max 200 tokens in, 50 tokens out.

Phase 3: NARRATIVE GENERATION (1 LLM call, bounded)
  Input: the Pydantic decision + raw numbers.
  Output: capped at 150 words. Hard stop via max_tokens.
  Never re-fetches data. Never reasons about data. Just writes.
```

Applied to Finance Guardian:

```
python# Phase 1 — pure Python, zero LLM
@dataclass
class FinancialSnapshot:
    tenant_id:       str
    mrr:             float
    mrr_change_pct:  float
    burn_rate:       float
    runway_days:     int
    bank_balance:    float
    prev_burn:       float
    similar_events:  list[dict]   # from Qdrant — fetched by code
    rule_anomalies:  list[str]    # pre-computed by if/elif rules

def assemble_snapshot(tenant_id: str) -> FinancialSnapshot:
    stripe  = fetch_stripe_metrics(tenant_id)
    bank    = fetch_bank_data(tenant_id)
    burn    = compute_burn(bank["transactions"])
    runway  = int(bank["balance"] / burn) if burn > 0 else 9999
    similar = qdrant_search(tenant_id, f"runway:{runway} mrr_change:{stripe['mrr_change_pct']:.1f}")
    
    # Rule engine — NO LLM
    anomalies = []
    if runway < 180:             anomalies.append("runway_critical")
    if stripe["mrr_change_pct"] < -0.10: anomalies.append("mrr_drop")
    if burn > prev_burn * 1.30:  anomalies.append("burn_spike")

    return FinancialSnapshot(
        tenant_id=tenant_id, mrr=stripe["mrr"],
        mrr_change_pct=stripe["mrr_change_pct"],
        burn_rate=burn, runway_days=runway,
        bank_balance=bank["balance"], prev_burn=prev_burn,
        similar_events=similar, rule_anomalies=anomalies,
    )


# Phase 2 — ONE small LLM call, Pydantic output
class AlertDecision(BaseModel):
    should_alert:   bool
    severity:       Literal["critical", "warning", "info"]
    primary_signal: str   # "runway_critical" | "mrr_drop" | "burn_spike" | "none"
    context_note:   str   # max 20 words: why LLM agrees/disagrees with rules

def decide_alert(snap: FinancialSnapshot) -> AlertDecision:
    if not snap.rule_anomalies:
        # Skip LLM entirely — no anomalies detected by rules
        return AlertDecision(should_alert=False, severity="info",
                             primary_signal="none", context_note="All metrics healthy.")

    # Only call LLM if rules flagged something
    # Inject ONLY numbers — no prose, no padding
    prompt = f"""Rules flagged: {snap.rule_anomalies}
Runway: {snap.runway_days}d | MRR Δ: {snap.mrr_change_pct:.1f}% | Burn: ${snap.burn_rate:,.0f}/mo
Similar past events: {[e['anomaly_type'] for e in snap.similar_events[:2]]}

Is this alert-worthy given context? Answer with the JSON schema provided."""

    return llm.with_structured_output(AlertDecision).invoke(prompt)
    # ~150 tokens in, ~40 tokens out. That's it.


# Phase 3 — bounded narrative, only if Phase 2 says alert
def generate_narrative(snap: FinancialSnapshot, decision: AlertDecision) -> str:
    if not decision.should_alert:
        return ""

    prompt = f"""Write a 80-word Slack alert. Severity: {decision.severity}.
Data: Runway {snap.runway_days}d, MRR {snap.mrr_change_pct:+.1f}%, Burn ${snap.burn_rate:,.0f}/mo, Balance ${snap.bank_balance:,.0f}
Context: {decision.context_note}
Start with emoji. End with one suggested action. No jargon."""

    return llm.invoke(prompt, max_tokens=120).content
    # ~100 tokens in, ~120 tokens out. Hard ceiling.
```

------

## Token Savings Per Agent Run

|                                | Before (fat LLM)   | After (thin LLM)                  |
| :----------------------------- | :----------------- | :-------------------------------- |
| Finance Guardian               | ~2,000 tokens/run  | ~320 tokens/run                   |
| BI Pulse                       | ~3,500 tokens/run  | ~500 tokens/run (NL→SQL is small) |
| Ops Watch                      | ~2,500 tokens/run  | ~400 tokens/run                   |
| Weekly Synthesis               | ~4,000 tokens/run  | ~800 tokens/run                   |
| **Total per day (3 tenants)**  | **~36,000 tokens** | **~6,000 tokens**                 |
| **Monthly cost (GPT-4o-mini)** | ~$1.08/month       | **~$0.18/month**                  |

An 83% token reduction — not from compression, but from only using the LLM where code genuinely cannot do the job.

------

## The Boundary Test

Before every LLM call in the codebase, apply this two-question test:

1. **Could an `if/elif` answer this?** → Use code.
2. **Could a SQL query answer this?** → Use SQL.

If both answers are no — the question requires judgment about ambiguity, synthesis across multiple signals, or natural language — that is the LLM's job. For Sarthi, that is roughly 3 calls per workflow instead of the current 8–12



### Token Budget Per Agent Run
| Agent | Before | After |
|---|---|---|
| Finance Guardian | ~2,000 tokens | ~320 tokens |
| BI Analyst | ~3,500 tokens | ~500 tokens |
| Ops Watch | ~2,500 tokens | ~400 tokens |
| Weekly Synthesis | ~4,000 tokens | ~800 tokens |
| **Monthly cost (3 tenants)** | **~$1.08** | **~$0.18** |

---

## 10. Memory Architecture — V3.0

### 5-Layer Memory Spine (Updated)

```
L1  REDIS (working memory)
    TTL: 1 hour
    Purpose: Current workflow context, session state
    Key format: f"tenant:{tenant_id}:{key}"

L2  QDRANT episodic (financial_events, metric_events, ops_events)
    TTL: 90 days then compressed
    Purpose: Raw event history, semantic similarity search
    Answers: "what past alerts are similar to this one?"

L3  GRAPHITI + NEO4J (semantic + temporal graph) ← REPLACES KUZU
    TTL: permanent
    Purpose: Entity relationships, causal chains, temporal edges,
             ACE playbook storage, evolving founder-specific strategies
    Answers: "what decisions followed this alert?"
             "which strategies has this founder rewarded?"
             "causal chain: burn spike → hire pause → runway recovery"

L4  POSTGRESQL procedural
    TTL: permanent
    Purpose: Learned agent behaviour, resolved blindspots, eval scores,
             founder feedback, APScheduler jobs, decisions, investor data

L5  QDRANT compressed
    TTL: permanent
    Purpose: Compressed episodic summaries (50-write trigger)
```

### Graphiti Entity Schema
| Entity | Properties | Key Relationships |
|---|---|---|
| `Decision` | decided, owner, domain, reversible, timestamp | MADE_BY→Founder, AFFECTS→Customer, CONNECTED_TO→Alert |
| `Alert` | blindspot_id, severity, confidence, threshold_used | RAISED_BY→Agent, PRECEDED_BY→Alert, RESPONDED_TO→Action |
| `Investor` | name, firm, priority, warm_up_days, last_contact | CONNECTED_TO→MetricTrend, MANAGED_BY→InvestorUpdateAgent |
| `Customer` | customer_id, mrr, plan, risk_score | AFFECTS→Alert, CHURNED_AFTER→Event |
| `Strategy` | domain, description, confidence_score, evidence_count | USED_BY→Agent, EVIDENCED_BY→Alert |
| `Session` | channel, start_time, messages_count | CONTAINS→Message, PRODUCES→Decision |
| `Agent` | name, domain, persona | GENERATED→Alert, OWNS→Strategy |
| `MissionState` | runway_days, burn_alert, churn_risk, active_alerts | READ_BY→Agent, UPDATED_AT→timestamp |

### Intent Node Extraction
Intent nodes are extracted automatically from founder messages containing uncertainty signals: "thinking", "maybe", "considering", "not sure", "should we". Confidence threshold: >0.7 before creating node. This lets future agents query "what is the founder currently thinking about?" without requiring an explicit decision log.

---

## 11. MissionState — Shared Context Object

```python
@dataclass
class MissionState:
    tenant_id:          str
    timestamp:          datetime
    # Finance domain
    runway_days:        int | None = None
    burn_alert:         bool = False
    burn_severity:      str | None = None
    # BI domain
    mrr_trend:          str | None = None   # "up" | "flat" | "down"
    churn_rate:         float | None = None
    # Ops domain
    churn_risk_users:   int = 0
    top_feature_ask:    str | None = None
    error_spike:        bool = False
    # Cross-agent signals
    active_alerts:      list[str] = field(default_factory=list)
    founder_focus:      str | None = None
```

All agents read MissionState before running. All agents write their domain fields after running. Stored in PostgreSQL `mission_states` table. Updated atomically.

---

## 12. Pydantic AI Output Contracts

Every LLM output is typed and validated. Auto-retry on schema violation.

```python
class AlertDecision(BaseModel):
    should_alert:   bool
    severity:       Literal["critical", "warning", "info"]
    primary_signal: str
    context_note:   str   # max 20 words

class GuardianMessage(BaseModel):
    pattern_name:     str
    insight:          str   # max 200 words, validated
    urgency_horizon:  str
    one_action:       str
    injected_numbers: list[str]   # audit trail

    @field_validator('insight')
    def max_200_words(cls, v):
        if len(v.split()) > 200:
            raise ValueError('Guardian message exceeds 200 words')
        return v
```

---

## 13. Slack Block Kit — Complete Interaction Surface

No web UI for the founder. All interaction via Slack buttons.

### Alert Block (Tier 2 — requires review)
```
[✓ Acknowledged] [📊 Show breakdown]
[🔁 Dispute]     [📌 Log decision]
```

### Decision Modal (/sarthi decide)
```
Decision: [_________________________]
Domain:   [Finance ▾]
Reversible: [● Yes  ○ No]
```

### Investor Update Approval (Two-key: Tier 3)
```
Aparna: [✓ Approved]
Sends when both approve.
```

### Weekly Brief Actions
```
[📌 Add decision] [📊 Full metrics] [🙋 Assign follow-up]
```

---

## 14. Correlation Agent

Runs AFTER all three domain agents complete. Reads MissionState. Finds cross-signal connections that individual agents cannot see. One synthesised Slack message per day maximum.

```python
CO_SIGNALS = {
    "burn_spike_plus_churn":       burn_alert AND churn_rate > 0.05,
    "error_spike_plus_churn_risk": error_spike AND churn_risk_users > 2,
    "short_runway_fundraising":    runway_days < 180 AND founder_focus == "fundraising",
}
# If no co-signals: no LLM call, no Slack message
# If co-signals: ONE LLM call, max 90 tokens out
```

---

## 15. Infrastructure — Azure Free Tier

All Sarthi infrastructure runs on Azure free tier: ₹0/month.
Only cost: OpenAI API (~$0.18/month for 3 tenants on GPT-4o-mini).

| Azure Service | Role | Free Limit |
|---|---|---|
| Container Apps | Python AI + Go API runtime | 180K vCPU-sec/month |
| PostgreSQL Flexible B1MS | All structured data | 750hrs · 32GB (12mo) |
| Cosmos DB (MongoDB API) | Vector memory (Qdrant alt on Azure) | 1,000 RU/s · 25GB always |
| Azure Functions | Webhook ingestion | 1M executions/month |
| Event Grid | Inter-agent pub/sub | 100K ops/month |
| Container Registry | Docker images | 100GB (12mo) |
| Azure DevOps | CI/CD pipelines | 5 users + unlimited pipelines |
| Static Web Apps | HTMX internal dashboard | 100GB bandwidth |
| Azure Monitor + App Insights | Infra + distributed traces | 5GB logs/month |
| Key Vault | Secrets management | 10K ops/month (12mo) |
| Entra ID B2C | OAuth / Identity | 50K MAU |
| Blob Storage | Traces, artifacts | 5GB LRS (12mo) |
| Langfuse (self-hosted ACA) | LLMOps traces + evals | Free (ACA allocation) |

### CI/CD Pipeline (Azure DevOps)
Push → Lint → pytest (real Postgres service container) → Docker build → ACR push → Container Apps rolling deploy → Smoke tests → Slack notification.

---

## 16. Observability Stack

| Layer | Tool | What It Covers |
|---|---|---|
| Infrastructure | Azure Monitor | CPU, memory, replicas, PostgreSQL, Event Grid |
| Distributed traces | App Insights SDK | Every HTTP request, LangGraph node timing |
| LLMOps | Langfuse (self-hosted) | Every LLM call: model, tokens, cost, ReAct trace, eval scores |
| Log analytics | Azure Log Analytics | KQL queries, agent history, APScheduler execution logs |
| Security | Microsoft Defender + Key Vault audit | Image scanning, secret access audit |

### SLOs
- Agent response to Slack: p95 < 30s
- Weekly brief delivery: by 7:10 AM Monday
- Error budget: ≤5 agent failures/day
- LLM cost spike: alert if 24h OpenAI spend > $2

---

## 17. Stack Decision Table — Final

| Component | Decision | Reason |
|---|---|---|
| **APScheduler** | ✅ Keep | Running, 10 jobs persisted in Postgres, verified |
| **Temporal** | ❌ Removed | APScheduler covers all scheduling needs at seed scale |
| **Neo4j + Graphiti** | ✅ Core (L3) | Temporal graph memory: episodic edges, playbook, entity resolution |
| **Kuzu** | ❌ Removed | Replaced by Neo4j + Graphiti entirely |
| **LangGraph** | ✅ Keep | Agent state machine. Already working. |
| **Pydantic AI** | ✅ Added | Enforces guardian message contract. Auto-retries malformed LLM output. |
| **DSPy** | ✅ Keep | Prompt optimisation layer. Works alongside Pydantic AI. |
| **Langfuse** | ✅ Keep | LLM quality monitoring. Non-negotiable for trust-based product. |
| **HTMX** | ✅ Added | Internal ops dashboard only. Founder never sees it. |
| **Redis** | ✅ Keep | L1 working memory. |
| **Qdrant** | ✅ Keep | Vector memory L2 + L5. |
| **PostgreSQL** | ✅ Keep | Structured data, APScheduler, decisions, investors. |
| **Azure Free Tier** | ✅ Keep | ₹0/month infra. 14 services mapped. |
| **Redpanda** | ❌ Removed | Replaced by Azure Event Grid on free tier. |

---

## 18. Pricing

| Tier | Price | Seats | Features |
|---|---|---|---|
| Beta | Free (60 days) | 1 | All 3 guardian agents, all alerts, investor update, ACE session |
| Solo Founder | $79/month | 1 | Full guardian, all watchlist, weekly eval, Graphiti memory |
| Seed Team | $199/month | Up to 5 | Above + custom thresholds, team channels, multi-session |

Beta → Paid conversion offer at Day 45.

---

## 19. Onboarding Success Metric

**Correct metric:** Founder acknowledged an insight they didn't already know within 48 hours of setup.

First alert must come from the watchlist — not a healthy-state pulse.
If no watchlist items triggered in first cycle: wait. Do not send "everything looks good."

---

## 20. Onboarding Flow (Slack DM)

```
Step 0: App installed → DM "I'm Sarthi. Setup takes 15 minutes."
Step 1: Finance Agent → Connect Stripe → Set runway alert threshold
Step 2: BI Agent → Connect Postgres (read-only user snippet provided)
Step 3: Ops Agent → Connect Sentry (optional)
Step 4: Company context → ICP, pricing model, top 3 metrics
Step 5: First guardian insight within 10 minutes of Stripe connection
```

Read-only Postgres snippet shipped verbatim:
```sql
CREATE USER sarthi_readonly WITH PASSWORD 'choose_a_password';
GRANT CONNECT ON DATABASE your_db_name TO sarthi_readonly;
GRANT USAGE ON SCHEMA public TO sarthi_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO sarthi_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT ON TABLES TO sarthi_readonly;
```

---

## 21. Database Schema — V3.0 Additions

```sql
-- Mission state (shared across all agents)
CREATE TABLE mission_states (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id   UUID REFERENCES tenants(id) UNIQUE,
  state       JSONB NOT NULL,
  updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Session messages (#sarthi channel history)
CREATE TABLE session_messages (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id   UUID REFERENCES tenants(id),
  role        TEXT NOT NULL,       -- 'founder' | 'finance' | 'bi' | 'ops' | 'sarthi'
  content     TEXT NOT NULL,
  agent_name  TEXT,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ACE playbook strategies (also in Graphiti — PG is audit log)
CREATE TABLE playbook_strategies (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id        UUID REFERENCES tenants(id),
  domain           TEXT NOT NULL,
  strategy         TEXT NOT NULL,
  confidence_score NUMERIC DEFAULT 1.0,
  evidence_count   INT DEFAULT 1,
  created_at       TIMESTAMPTZ DEFAULT NOW(),
  updated_at       TIMESTAMPTZ DEFAULT NOW()
);

-- Investor relationships (V2 — verified working)
CREATE TABLE investor_relationships (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       UUID REFERENCES tenants(id),
  investor_name   TEXT NOT NULL,
  firm            TEXT,
  last_contact_at TIMESTAMPTZ,
  warm_up_days    INT DEFAULT 30,
  raise_priority  INT DEFAULT 3,
  notes           TEXT,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Existing V2 additions (keep all):
-- agent_alerts (+ insight_acknowledged, insight_already_knew, blindspot_id)
-- resolved_blindspots
-- eval_scores
-- onboarding_events
-- decisions (+ logged_by_slack_id, owner, domain, is_reversible)
```

---

## 22. File Structure — V3.0 Complete

```
apps/
  ai/
    src/
      agents/
        finance/
          graph.py          ← v2.0 ✅ KEEP
          signatures.py     ← v2.0 ✅ EXTEND (add Pydantic AI output)
          thresholds.py     ← v2.0 ✅ KEEP
        bi/
          graph.py          ← v2.0 ✅ KEEP
          nl_to_sql.py      ← v2.0 ✅ KEEP
        ops/
          graph.py          ← v2.0 ✅ KEEP
        cofounder/          ← NEW
          router.py         ← routes messages to employee agents
          reflector.py      ← ACE Reflector: reads founder response
          curator.py        ← ACE Curator: updates Graphiti playbook
          correlation.py    ← cross-signal detection + synthesis

      session/              ← NEW
        context.py          ← get_session_context(): last N messages
        relevance_gate.py   ← keyword + MissionState based routing
        mission_state.py    ← MissionState dataclass + read/write

      guardian/             ← v2.0 ✅ KEEP
        watchlist.py
        detector.py
        insight_builder.py

      schemas/               ← UPDATED for V3.0
        event_envelope.py     ← v2.0 ✅ KEEP
        desk_results.py    ← v2.0 ✅ KEEP
        guardian.py       ← v3.0 ✅ NEW: Pydantic AI output contracts

      memory/               ← UPDATED
        spine.py            ← orchestrates all 5 layers
        working.py          ← L1 Redis (unchanged)
        episodic.py         ← L2 Qdrant (unchanged)
        semantic.py         ← L3 UPDATED: Graphiti replaces Kuzu
        procedural.py       ← L4 PostgreSQL (unchanged)
        compressed.py       ← L5 Qdrant (unchanged)
        rag_kernel.py       ← unchanged
        compressor.py       ← unchanged

      hitl/                 ← v2.0 ✅ KEEP
        manager.py
        confidence.py

      llmops/               ← v2.0 ✅ KEEP
        tracer.py
        eval_loop.py
        self_analysis.py

      dashboard/            ← NEW (HTMX internal ops)
        routes.py           ← /internal/alerts, /watchlist, /hitl-queue, /eval-scores
        templates/          ← HTMX partials

      integrations/
        stripe_client.py    ← v2.0 ✅ KEEP
        plaid_client.py     ← v2.0 ✅ KEEP
        qdrant_client.py    ← v2.0 ✅ KEEP
        slack_client.py     ← v2.0 ✅ EXTEND (multi-persona bot posting)
        langfuse_client.py  ← v2.0 ✅ KEEP
        db_client.py        ← v2.0 ✅ KEEP
        graphiti_client.py  ← NEW

      scheduler/
        sarthi_scheduler.py ← v2.0 ✅ KEEP (APScheduler, 10 jobs)
        slackbot.py         ← v2.0 ✅ EXTEND (relevance gate + session write)

  core/
    cmd/server/main.go      ← v2.0 ✅ KEEP (+ /slack/commands proxy)

tests/
  unit/
    test_agents/            ← v2.0 ✅ 119 PASSING — DO NOT TOUCH
    test_guardian/          ← v2.0 ✅ 20 tests
    test_memory/            ← v2.0 ✅ 30 tests (update semantic layer tests)
    test_hitl/              ← v2.0 ✅ 10 tests
    test_llmops/            ← v2.0 ✅ 15 tests
    test_session/           ← NEW (target: 15 tests)
    test_cofounder/         ← NEW (target: 15 tests)
  integration/
    test_workflows/         ← v2.0 ✅ keep
    test_investor_warmup.py ← v2.0 ✅ 5 tests
  e2e/
    test_decision_journal_e2e.py ← v2.0 ✅
    test_scheduler.py            ← v2.0 ✅
```

---

## 23. Test Targets — V3.0

| Phase | New Tests | Cumulative | Regressions |
|---|---|---|---|
| V2.0 baseline | — | 194 | — |
| + Pydantic contracts | +5 updated | 194 | 0 |
| + Graphiti semantic layer | +5 updated | 194 | 0 |
| + Session layer | 15 new | 209 | 0 |
| + Co-founder agent | 15 new | 224 | 0 |
| **V3.0 complete** | **30 new** | **224** | **0** |

---

## 24. Build Order — V3.0 Strict

```
Step 1: Pydantic AI contracts (guardian message contracts)
  [x] Write apps/ai/src/schemas/guardian.py
  [x] AlertDecision schema (should_alert, severity, primary_signal, context_note)
  [x] GuardianMessage schema (pattern_name, insight, urgency_horizon, one_action, injected_numbers)
  [x] Word-limit validation (insight max 200 words, context_note max 20 words)
  [x] Injected numbers audit trail

Step 2: Replace Kuzu with Graphiti in memory/semantic.py
  [x] pip install graphiti-core neo4j
  [x] Update memory/semantic.py to use Graphiti
  [x] Add graphiti_client.py (integrated, no new file)
  [x] Run existing 194 tests → must still pass
  [ ] Update docker-compose: add neo4j service (optional - uses existing opscore-neo4j)

Step 3: MissionState + session layer (pure Python, no LLM)
  [x] Write session/mission_state.py
  [x] Write session/context.py
  [x] Write session/relevance_gate.py
  [x] Add mission_states + session_messages DB tables (001_session_layer.sql)
  [ ] Write tests/unit/test_session/ (15 tests)
  [ ] Run all tests → 209 passing, 0 regressions

Step 4: Co-founder agent (manager layer)
  [x] Write cofounder/router.py
  [x] Write cofounder/reflector.py
  [x] Write cofounder/curator.py
  [x] Write cofounder/correlation.py
  [x] Update slack_client.py for multi-persona posting (existing)
  [ ] Write tests/unit/test_cofounder/ (15 tests)
  [ ] Run all tests → 224 passing, 0 regressions

Step 5: Wire relevance gate into slackbot.py
  [ ] On every incoming #sarthi message:
      - write to session_messages
      - run relevance_gate for each domain
      - trigger relevant employee agents
      - update MissionState after each agent completes
      - run correlation agent last
  [ ] Run all tests → 224 passing, 0 regressions

Step 6: HTMX internal dashboard
  [ ] Write dashboard/routes.py
  [ ] Write dashboard/templates/
  [ ] Alerts queue, watchlist status, HITL queue, eval scores
  [ ] No auth required (internal only, no public exposure)

Step 7: Azure deployment
  [ ] Follow Azure Free Tier Blueprint (Section 15)
  [ ] Set SLACK_BOT_TOKEN at api.slack.com/apps
  [ ] Verify /sarthi decide works end-to-end on Azure
```

---

## 25. Fallback Contract (Non-Negotiable)

Every new system degrades gracefully. The guardian only fails if the agent fails.

```python
# MANDATORY pattern in every agent node:

# Graphiti — optional, graceful fallback
graph_context = []
try:
    if graphiti_client.available():
        graph_context = await graphiti_client.search(tenant_id, query)
except Exception:
    graph_context = []    # graph down → empty context → agent still runs

# MissionState — optional, graceful fallback
mission = MissionState(tenant_id=tenant_id, timestamp=datetime.utcnow())
try:
    mission = await get_mission_state(tenant_id)
except Exception:
    pass    # use empty mission state

# Correlation agent — optional, never blocks employee agents
try:
    await run_correlation(tenant_id)
except Exception:
    pass    # correlation down → employee agents already posted
```

---

## 26. Guardian Alert Rules (Non-Negotiable)

```
RULE 1: Numbers are NEVER generated by LLM.
  All financial numbers, metrics, dates injected from data sources.
  LLM writes narrative. Never invents quantities.

RULE 2: Guardian message structure is always:
  Pattern name → Number (injected) → Why it matters →
  Urgency horizon → Historical precedent → One concrete action.
  Always prose. Never bullets.

RULE 3: First alert must come from the watchlist.
  If no watchlist items triggered: wait for next cycle.
  Never send "everything looks good."

RULE 4: Max 3 alerts per day per tenant.
  Same blindspot_id cannot fire within 48 hours.
  Info alerts accumulate into weekly digest.

RULE 5: Tenant isolation is absolute.
  Every Qdrant query: filter by tenant_id.
  Every DB query: WHERE tenant_id = %s.
  Every Redis key: f"tenant:{tenant_id}:{key}"
  Every Graphiti query: group_ids=[tenant_id]
```

---

## Open Questions — Resolved

1. **Temporal vs APScheduler** → APScheduler. Running, verified, 10 jobs persisted.
2. **Kuzu vs Neo4j+Graphiti** → Neo4j + Graphiti. Temporal edges are the moat.
3. **Co-founder agent authority** → Option C: decides low severity, escalates critical conflicts.
4. **Intent node extraction** → Automatic on uncertainty signals, confidence threshold >0.7.
5. **ACE framework** → Stanford ACE (Generator→Reflector→Curator). YouTube ACE not launched.
6. **Redpanda vs Azure Event Grid** → Azure Event Grid (free tier, no container needed).
7. **Multi-persona Slack** → 3 named bot personas + 1 synthesis identity (Sarthi).
8. **Infrastructure** → Azure Free Tier, ₹0/month, 14 services mapped.
9. **OpenRouter vs Qwen3** → OpenRouter GPT-4o-mini for beta. Qwen3-4B Phase 2.
10. **Single vs multi-tenant Qdrant** → tenant_id in all payloads from Day 1.

---

## 27. Dual-Path Demo Strategy

Sarthi V3.0 supports two distinct demonstration paths — one for **live interviews** and one for **portfolio showcase**.

### Path 1: Production (Azure Free Tier)

The primary path documented throughout this PRD. Deploys to Azure Container Apps with:

- 14 Azure services on free tier (₹0/month infrastructure)
- APScheduler persisted to PostgreSQL
- Graphiti episodic memory to Neo4j
- OpenAI API (~$0.18/month for 3 tenants)

**Use case:** Production deployment, real-time operation.

### Path 2: Local Showcase (k3d/Helm)

For portfolio demonstrations when live Azure isn't available. Uses:

- **k3d** (Kubernetes in Docker) for local k8s cluster
- **Helm charts** for all 5 services + observability stack
- **Custom Alpine-based images** for minimal container size
- **Temporal** (re-added) — durable workflow execution for portfolio credibility
- **Redpanda** (re-added) — Kafka-compatible event bus

**Use case:** "Show me the code" portfolio demos, technical deep-dives.

| Component | Path 1 (Production) | Path 2 (Local Showcase) |
|-----------|---------------------|------------------------|
| Orchestration | APScheduler | APScheduler + Temporal |
| Event Bus | Azure Event Grid | Redpanda |
| Scheduler | APScheduler (Postgres) | APScheduler (Postgres) |
| Demo Method | Live webhook → trace | k3d apply → kubectl port-forward |

### Interview Demo: Primary Method

For live interviews, **Docker Compose is the primary method**:

```bash
# 1. Bring everything up
make up && make obs

# 2. Fire a webhook
curl -X POST http://sarthi.local/webhooks/stripe \
  -H "Content-Type: application/json" \
  -d '{"type":"invoice.payment_failed","tenant_id":"test-001"}'

# 3. Open Jaeger — show the 5-service trace waterfall
open http://jaeger.local

# 4. Show Grafana dashboards live
open http://grafana.local

# 5. Kill decision-engine, show graceful degradation
docker stop sarthi-decision-engine
curl -X POST http://sarthi.local/webhooks/stripe \
  -d '{"type":"invoice.payment_failed","tenant_id":"test-001"}'
# Show system still responds, does not crash
docker start sarthi-decision-engine
```

This demonstrates:
- Real distributed tracing (opentelemetry)
- Service resilience (graceful degradation)
- Microservices communication patterns (webhook → worker → trace)
- Observability stack in action (Jaeger, Grafana)

### k3d: Portfolio Layer

k3d is a **secondary path** — show as code, not run live:

```bash
# Build custom Alpine images
make docker-build-alpine

# Create k3d cluster
k3d cluster create sarthi

# Apply Helm charts
helm install sarthi ./helm/sarthi

# Show Kubernetes manifest depth
kubectl get all -n sarthi
kubectl get ingress -n sarthi
```

**k3d is documented for portfolio depth, not required for interviews.**

### What Has Been Built

| Component | Status | Notes |
|-----------|--------|-------|
| 5 microservices | ✅ Implemented | decision-engine, api-gateway, worker, observer, scheduler |
| OTel tracing | ✅ Implemented | 5-service waterfall |
| Custom Alpine images | ✅ Implemented | Minimal base for portfolio |
| Helm charts | ✅ Implemented | Full k8s deployment |
| Docker Compose | ✅ Primary | Interview demos |
| k3d manifests | ✅ Secondary | Portfolio "show as code" |

---

*Built for the solo founder who has everything except the team. Sarthi gives you the team.*

---
Version 3.0 · April 26, 2026 · Engineering-Ready
