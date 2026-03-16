-- Column to track status of the most recent health check
ALTER TABLE public.monitors
    ADD COLUMN IF NOT EXISTS last_check_success BOOLEAN;
