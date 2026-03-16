-- Alert rules defining notification triggers for monitors
CREATE TABLE IF NOT EXISTS public.alert_rules (
    id                      UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
    monitor_id              UUID    NOT NULL REFERENCES public.monitors(id) ON DELETE CASCADE,
    alert_type              TEXT    NOT NULL CHECK (alert_type IN ('email', 'slack', 'webhook')),
    target                  TEXT    NOT NULL CHECK (char_length(target) BETWEEN 1 AND 2048),
    threshold_down_minutes  INTEGER NOT NULL DEFAULT 5  CHECK (threshold_down_minutes >= 1),
    cooldown_minutes        INTEGER NOT NULL DEFAULT 30 CHECK (cooldown_minutes >= 5),
    is_active               BOOLEAN NOT NULL DEFAULT true,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for looking up rules by monitor
CREATE INDEX IF NOT EXISTS idx_alert_rules_monitor_id
    ON public.alert_rules (monitor_id);

-- Partial index for active rule evaluation
CREATE INDEX IF NOT EXISTS idx_alert_rules_active
    ON public.alert_rules (monitor_id)
    WHERE is_active = true;

-- Enable Row-Level Security
ALTER TABLE public.alert_rules ENABLE ROW LEVEL SECURITY;

-- Allow users to view alert rules for their own monitors
DROP POLICY IF EXISTS "Users can view alert rules for their monitors" ON public.alert_rules;
CREATE POLICY "Users can view alert rules for their monitors"
    ON public.alert_rules
    FOR SELECT
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.monitors
            WHERE monitors.id = alert_rules.monitor_id
              AND monitors.user_id = (SELECT auth.uid())
        )
    );

-- Allow users to create alert rules for their own monitors
DROP POLICY IF EXISTS "Users can create alert rules for their monitors" ON public.alert_rules;
CREATE POLICY "Users can create alert rules for their monitors"
    ON public.alert_rules
    FOR INSERT
    TO authenticated
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.monitors
            WHERE monitors.id = alert_rules.monitor_id
              AND monitors.user_id = (SELECT auth.uid())
        )
    );

-- Allow users to update alert rules for their own monitors
DROP POLICY IF EXISTS "Users can update alert rules for their monitors" ON public.alert_rules;
CREATE POLICY "Users can update alert rules for their monitors"
    ON public.alert_rules
    FOR UPDATE
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.monitors
            WHERE monitors.id = alert_rules.monitor_id
              AND monitors.user_id = (SELECT auth.uid())
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.monitors
            WHERE monitors.id = alert_rules.monitor_id
              AND monitors.user_id = (SELECT auth.uid())
        )
    );

-- Allow users to delete alert rules for their own monitors
DROP POLICY IF EXISTS "Users can delete alert rules for their monitors" ON public.alert_rules;
CREATE POLICY "Users can delete alert rules for their monitors"
    ON public.alert_rules
    FOR DELETE
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.monitors
            WHERE monitors.id = alert_rules.monitor_id
              AND monitors.user_id = (SELECT auth.uid())
        )
    );
