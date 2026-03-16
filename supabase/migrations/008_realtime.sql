-- Enable Realtime for monitors table
DO $$ BEGIN
    ALTER PUBLICATION supabase_realtime ADD TABLE public.monitors;
EXCEPTION WHEN duplicate_object THEN
    NULL;
END $$;

-- Enable Realtime for check_results table
DO $$ BEGIN
    ALTER PUBLICATION supabase_realtime ADD TABLE public.check_results;
EXCEPTION WHEN duplicate_object THEN
    NULL;
END $$;

-- Enable Realtime for alert_history table
DO $$ BEGIN
    ALTER PUBLICATION supabase_realtime ADD TABLE public.alert_history;
EXCEPTION WHEN duplicate_object THEN
    NULL;
END $$;
