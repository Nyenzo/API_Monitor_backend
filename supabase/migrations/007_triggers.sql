-- Trigger function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
SET search_path = ''
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

-- Update profiles.updated_at on row modification
DROP TRIGGER IF EXISTS set_profiles_updated_at ON public.profiles;
CREATE TRIGGER set_profiles_updated_at
    BEFORE UPDATE ON public.profiles
    FOR EACH ROW
    WHEN (OLD IS DISTINCT FROM NEW)
    EXECUTE FUNCTION public.set_updated_at();

-- Update monitors.updated_at on row modification
DROP TRIGGER IF EXISTS set_monitors_updated_at ON public.monitors;
CREATE TRIGGER set_monitors_updated_at
    BEFORE UPDATE ON public.monitors
    FOR EACH ROW
    WHEN (OLD IS DISTINCT FROM NEW)
    EXECUTE FUNCTION public.set_updated_at();

-- Update alert_rules.updated_at on row modification
DROP TRIGGER IF EXISTS set_alert_rules_updated_at ON public.alert_rules;
CREATE TRIGGER set_alert_rules_updated_at
    BEFORE UPDATE ON public.alert_rules
    FOR EACH ROW
    WHEN (OLD IS DISTINCT FROM NEW)
    EXECUTE FUNCTION public.set_updated_at();

-- RPC function to fetch monitors due for a health check
CREATE OR REPLACE FUNCTION public.get_due_monitors()
RETURNS SETOF public.monitors
LANGUAGE sql
STABLE
SET search_path = ''
AS $$
    SELECT *
    FROM public.monitors
    WHERE is_active = true
      AND (
          last_checked_at IS NULL
          OR last_checked_at + (interval_seconds || ' seconds')::interval <= now()
      )
    ORDER BY last_checked_at NULLS FIRST;
$$;
