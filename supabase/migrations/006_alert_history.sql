-- Alert history table logging notification events
CREATE TABLE IF NOT EXISTS public.alert_history (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_rule_id   UUID        NOT NULL REFERENCES public.alert_rules(id) ON DELETE CASCADE,
    triggered_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at     TIMESTAMPTZ,
    status          TEXT        NOT NULL DEFAULT 'triggered'
                                CHECK (status IN ('triggered', 'sent', 'failed', 'resolved')),
    payload         JSONB       NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for fetching history per rule in reverse chronological order
CREATE INDEX IF NOT EXISTS idx_alert_history_rule_id
    ON public.alert_history (alert_rule_id, triggered_at DESC);

-- Partial index for filtering by failed or triggered status
CREATE INDEX IF NOT EXISTS idx_alert_history_status
    ON public.alert_history (status)
    WHERE status IN ('failed', 'triggered');

-- Enable Row-Level Security
ALTER TABLE public.alert_history ENABLE ROW LEVEL SECURITY;

-- Allow users to view alert history for their own monitors
DROP POLICY IF EXISTS "Users can view alert history for their monitors" ON public.alert_history;
CREATE POLICY "Users can view alert history for their monitors"
    ON public.alert_history
    FOR SELECT
    TO authenticated
    USING (
        EXISTS (
            SELECT 1
            FROM public.alert_rules
            JOIN public.monitors ON monitors.id = alert_rules.monitor_id
            WHERE alert_rules.id = alert_history.alert_rule_id
              AND monitors.user_id = (SELECT auth.uid())
        )
    );

-- Allow service role to insert alert history
DROP POLICY IF EXISTS "Service role can insert alert history" ON public.alert_history;
CREATE POLICY "Service role can insert alert history"
    ON public.alert_history
    FOR INSERT
    TO service_role
    WITH CHECK (true);

-- Allow service role to update alert history
DROP POLICY IF EXISTS "Service role can update alert history" ON public.alert_history;
CREATE POLICY "Service role can update alert history"
    ON public.alert_history
    FOR UPDATE
    TO service_role
    USING (true)
    WITH CHECK (true);
