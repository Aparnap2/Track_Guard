# V2.0 Legacy Code (Archived May 2026)

## Migration Date
Archived: May 2026

## Why Archived
Migrated to V3.0 per PRD Section 27 (Dual-Path Demo Strategy).

## What Was Migrated

### Agents
| V2.0 Agent | New Location | Notes |
|------------|--------------|-------|
| `pulse` | → BI Analyst | Still available in legacy |
| `anomaly` | → Ops Watch | Still available in legacy |
| `investor` | → kept in production | Still available in legacy |
| `qa` | → kept in production | Still available in legacy |
| `hiring` | → kept in production | Still available in legacy |
| `comms` | → kept in production | Still available in legacy |

### Memory
| V2.0 Memory | Status |
|-------------|--------|
| `spine.py` | → Replaced by services/memory/ |
| `state_manager.py` | → Replaced by MissionState (not yet implemented) |
| `rag_kernel.py` | → Removed per PRD (RAG kernel gone) |
| `compressor.py` | → Kept (L5 compressed memory) |

## V2.0 Test Count
194 passing tests — all preserved.

## To Restore (if needed)
```bash
# Restore agents
mv legacy/agents/v2/* agents/

# Restore memory
mv legacy/memory/v2/* memory/
```

## V3.0 PRD Reference
See: `../../../sarthi-v3-0-product-requirements-document.md`