-- Migration 003: Add derived finance + guardrail fields to mission_states
ALTER TABLE mission_states ADD COLUMN IF NOT EXISTS burn_multiple NUMERIC;
ALTER TABLE mission_states ADD COLUMN IF NOT EXISTS effective_runway_days INT;
ALTER TABLE mission_states ADD COLUMN IF NOT EXISTS working_capital_ratio NUMERIC;
ALTER TABLE mission_states ADD COLUMN IF NOT EXISTS npv_last_decision NUMERIC;
ALTER TABLE mission_states ADD COLUMN IF NOT EXISTS wacc_estimate NUMERIC;
ALTER TABLE mission_states ADD COLUMN IF NOT EXISTS last_approval_tier TEXT;
ALTER TABLE mission_states ADD COLUMN IF NOT EXISTS last_reversible BOOLEAN;
ALTER TABLE mission_states ADD COLUMN IF NOT EXISTS active_authority_limit TEXT;
ALTER TABLE mission_states ADD COLUMN IF NOT EXISTS guardrail_override_reason TEXT;
ALTER TABLE mission_states ADD COLUMN IF NOT EXISTS guardrail_risk_type TEXT;
ALTER TABLE mission_states ADD COLUMN IF NOT EXISTS guardrail_blocking BOOLEAN DEFAULT FALSE;
ALTER TABLE mission_states ADD COLUMN IF NOT EXISTS investor_facing_alert BOOLEAN DEFAULT FALSE;
