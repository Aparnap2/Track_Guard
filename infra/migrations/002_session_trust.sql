-- 002_session_trust.sql - V3.0 Trust Battery tables
-- Per PRD: agent_trust_profiles + agent_trust_events

-- agent_trust_profiles: Trust score per agent per tenant
-- Per PRD: Track trust_score, mode (normal|degraded|suspended)
CREATE TABLE IF NOT EXISTS agent_trust_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    agent_name TEXT NOT NULL,
    trust_score NUMERIC(3, 2) DEFAULT 0.75,  -- 0.00-1.00
    mode TEXT DEFAULT 'normal' CHECK (mode IN ('normal', 'degraded', 'suspended')),
    failure_count INTEGER DEFAULT 0,
    last_success_at TIMESTAMPTZ,
    last_failure_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(tenant_id, agent_name)
);

CREATE INDEX IF NOT EXISTS idx_agent_trust_profiles_tenant_agent
    ON agent_trust_profiles(tenant_id, agent_name);

CREATE INDEX IF NOT EXISTS idx_agent_trust_profiles_trust_score
    ON agent_trust_profiles(trust_score);

CREATE INDEX IF NOT EXISTS idx_agent_trust_profiles_mode
    ON agent_trust_profiles(mode);

-- agent_trust_events: Event log for trust score changes
-- Per PRD: score_update, mode_change, recovery events
CREATE TABLE IF NOT EXISTS agent_trust_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    agent_name TEXT NOT NULL,
    event_type TEXT NOT NULL CHECK (event_type IN ('score_update', 'mode_change', 'recovery')),
    old_score NUMERIC(3, 2),
    new_score NUMERIC(3, 2),
    old_mode TEXT,
    new_mode TEXT,
    reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_trust_events_tenant_agent
    ON agent_trust_events(tenant_id, agent_name, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_agent_trust_events_created
    ON agent_trust_events(created_at DESC);

-- Function to update trust profile and log event atomically
CREATE OR REPLACE FUNCTION update_agent_trust(
    p_tenant_id UUID,
    p_agent_name TEXT,
    p_new_score NUMERIC(3, 2),
    p_event_type TEXT,
    p_reason TEXT DEFAULT NULL
) RETURNS VOID AS $$
DECLARE
    v_old_score NUMERIC(3, 2);
    v_old_mode TEXT;
BEGIN
    -- Get current values
    SELECT trust_score, mode INTO v_old_score, v_old_mode
    FROM agent_trust_profiles
    WHERE tenant_id = p_tenant_id AND agent_name = p_agent_name;

    -- If not exists, create with default values
    IF v_old_score IS NULL THEN
        v_old_score := 0.75;
        v_old_mode := 'normal';
        INSERT INTO agent_trust_profiles (tenant_id, agent_name, trust_score, mode)
        VALUES (p_tenant_id, p_agent_name, v_old_score, v_old_mode)
        ON CONFLICT (tenant_id, agent_name) DO NOTHING;
    END IF;

    -- Determine new mode based on score
    DECLARE
        v_new_mode TEXT;
    BEGIN
        IF p_new_score < 0.4 THEN
            v_new_mode := 'degraded';
        ELSIF p_new_score < 0.2 THEN
            v_new_mode := 'suspended';
        ELSE
            v_new_mode := 'normal';
        END IF;
    END;

    -- Update profile
    UPDATE agent_trust_profiles
    SET trust_score = p_new_score,
        mode = v_new_mode,
        last_success_at = CASE WHEN p_event_type = 'score_update' AND p_new_score > v_old_score THEN NOW() ELSE last_success_at END,
        last_failure_at = CASE WHEN p_event_type = 'score_update' AND p_new_score < v_old_score THEN NOW() ELSE last_failure_at END,
        failure_count = CASE WHEN p_new_score < v_old_score THEN failure_count + 1 ELSE failure_count END,
        updated_at = NOW()
    WHERE tenant_id = p_tenant_id AND agent_name = p_agent_name;

    -- Log event
    INSERT INTO agent_trust_events (tenant_id, agent_name, event_type, old_score, new_score, old_mode, new_mode, reason)
    VALUES (p_tenant_id, p_agent_name, p_event_type, v_old_score, p_new_score, v_old_mode, v_new_mode, p_reason);
END;
$$ LANGUAGE plpgsql;