-- Monitors table for tracking endpoint health
CREATE TABLE IF NOT EXISTS public.monitors (
    id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 UUID        NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    name                    TEXT        NOT NULL CHECK (char_length(name) BETWEEN 1 AND 255),
    url                     TEXT        NOT NULL CHECK (url ~ '^https?://'),
    method                  TEXT        NOT NULL DEFAULT 'GET'
                                        CHECK (method IN ('GET','POST','PUT','PATCH','DELETE','HEAD','OPTIONS')),
    headers                 JSONB       NOT NULL DEFAULT '{}'::jsonb,
    body                    TEXT        NOT NULL DEFAULT '',
    interval_seconds        INTEGER     NOT NULL DEFAULT 300
                                        CHECK (interval_seconds >= 30 AND interval_seconds <= 86400),
    timeout_ms              INTEGER     NOT NULL DEFAULT 10000
                                        CHECK (timeout_ms >= 1000 AND timeout_ms <= 60000),
    expected_status         INTEGER     NOT NULL DEFAULT 200
                                        CHECK (expected_status >= 100 AND expected_status <= 599),
    expected_body_contains  TEXT        NOT NULL DEFAULT '',
    is_active               BOOLEAN     NOT NULL DEFAULT true,
    last_checked_at         TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
) WITH (fillfactor = 70);

-- Index for filtering monitors by user and status
CREATE INDEX IF NOT EXISTS idx_monitors_user_id
    ON public.monitors (user_id, is_active);

-- Partial index for health check scheduling
CREATE INDEX IF NOT EXISTS idx_monitors_active_check
    ON public.monitors (last_checked_at NULLS FIRST)
    WHERE is_active = true;

-- Index for ordering monitors by creation date
CREATE INDEX IF NOT EXISTS idx_monitors_user_created
    ON public.monitors (user_id, created_at DESC);

-- Enable Row-Level Security
ALTER TABLE public.monitors ENABLE ROW LEVEL SECURITY;

-- Allow users to view their own monitors
DROP POLICY IF EXISTS "Users can view their own monitors" ON public.monitors;
CREATE POLICY "Users can view their own monitors"
    ON public.monitors
    FOR SELECT
    TO authenticated
    USING ((SELECT auth.uid()) = user_id);

-- Allow users to create their own monitors
DROP POLICY IF EXISTS "Users can create their own monitors" ON public.monitors;
CREATE POLICY "Users can create their own monitors"
    ON public.monitors
    FOR INSERT
    TO authenticated
    WITH CHECK ((SELECT auth.uid()) = user_id);

-- Allow users to update their own monitors
DROP POLICY IF EXISTS "Users can update their own monitors" ON public.monitors;
CREATE POLICY "Users can update their own monitors"
    ON public.monitors
    FOR UPDATE
    TO authenticated
    USING  ((SELECT auth.uid()) = user_id)
    WITH CHECK ((SELECT auth.uid()) = user_id);

-- Allow users to delete their own monitors
DROP POLICY IF EXISTS "Users can delete their own monitors" ON public.monitors;
CREATE POLICY "Users can delete their own monitors"
    ON public.monitors
    FOR DELETE
    TO authenticated
    USING ((SELECT auth.uid()) = user_id);
