-- Check results table for health-check response history
CREATE TABLE IF NOT EXISTS public.check_results (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    monitor_id          UUID        NOT NULL REFERENCES public.monitors(id) ON DELETE CASCADE,
    timestamp           TIMESTAMPTZ NOT NULL DEFAULT now(),
    status_code         INTEGER,
    response_time_ms    INTEGER,
    success             BOOLEAN     NOT NULL DEFAULT false,
    response_size_bytes INTEGER     NOT NULL DEFAULT 0,
    error_message       TEXT        NOT NULL DEFAULT '',
    response_snippet    TEXT        NOT NULL DEFAULT '',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for fetching results per monitor ordered by time
CREATE INDEX IF NOT EXISTS idx_check_results_monitor_ts
    ON public.check_results (monitor_id, timestamp DESC);

-- Index for alert evaluation filtering failures
CREATE INDEX IF NOT EXISTS idx_check_results_monitor_success
    ON public.check_results (monitor_id, success, timestamp DESC);

-- Enable Row-Level Security
ALTER TABLE public.check_results ENABLE ROW LEVEL SECURITY;

-- Allow users to view results for their own monitors
DROP POLICY IF EXISTS "Users can view check results for their monitors" ON public.check_results;
CREATE POLICY "Users can view check results for their monitors"
    ON public.check_results
    FOR SELECT
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.monitors
            WHERE monitors.id = check_results.monitor_id
              AND monitors.user_id = (SELECT auth.uid())
        )
    );

-- Allow service role to insert check results
DROP POLICY IF EXISTS "Service role can insert check results" ON public.check_results;
CREATE POLICY "Service role can insert check results"
    ON public.check_results
    FOR INSERT
    TO service_role
    WITH CHECK (true);
