ALTER TABLE public.monitors
    ADD COLUMN IF NOT EXISTS check_lease_until TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_monitors_due_checks
    ON public.monitors (check_lease_until, last_checked_at NULLS FIRST)
    WHERE is_active = true;

DROP FUNCTION IF EXISTS public.get_due_monitors();

CREATE OR REPLACE FUNCTION public.get_due_monitors(batch_size INTEGER DEFAULT 500)
RETURNS SETOF public.monitors
LANGUAGE sql
VOLATILE
SET search_path = ''
AS $$
    WITH due_monitors AS (
        SELECT id
        FROM public.monitors
        WHERE is_active = true
          AND (check_lease_until IS NULL OR check_lease_until <= now())
          AND (
              last_checked_at IS NULL
              OR last_checked_at + make_interval(secs => interval_seconds) <= now()
          )
        ORDER BY last_checked_at NULLS FIRST
        FOR UPDATE SKIP LOCKED
        LIMIT LEAST(GREATEST(batch_size, 1), 1000)
    ), leased_monitors AS (
        UPDATE public.monitors AS monitor
        SET check_lease_until = now() + make_interval(
            secs => GREATEST(60, CEIL(monitor.timeout_ms / 1000.0)::INTEGER + 30)
        )
        FROM due_monitors
        WHERE monitor.id = due_monitors.id
        RETURNING monitor.*
    )
    SELECT * FROM leased_monitors;
$$;
