ALTER TABLE public.monitors
    ADD COLUMN IF NOT EXISTS monitor_kind TEXT NOT NULL DEFAULT 'uptime'
        CHECK (monitor_kind IN ('uptime', 'contract')),
    ADD COLUMN IF NOT EXISTS contract_operation_id TEXT,
    ADD COLUMN IF NOT EXISTS required_json_paths JSONB NOT NULL DEFAULT '[]'::jsonb
        CHECK (jsonb_typeof(required_json_paths) = 'array');

CREATE INDEX IF NOT EXISTS idx_monitors_user_contract
    ON public.monitors (user_id, created_at DESC)
    WHERE monitor_kind = 'contract';

CREATE TABLE IF NOT EXISTS public.release_verifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    deployment_ref TEXT NOT NULL CHECK (char_length(deployment_ref) BETWEEN 1 AND 255),
    status TEXT NOT NULL DEFAULT 'running'
        CHECK (status IN ('running', 'passed', 'regressed', 'incomplete')),
    total_checks INTEGER NOT NULL DEFAULT 0 CHECK (total_checks >= 0),
    passed_checks INTEGER NOT NULL DEFAULT 0 CHECK (passed_checks >= 0),
    failed_checks INTEGER NOT NULL DEFAULT 0 CHECK (failed_checks >= 0),
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_release_verifications_user_started
    ON public.release_verifications (user_id, started_at DESC);

ALTER TABLE public.release_verifications ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own release verifications"
    ON public.release_verifications
    FOR SELECT TO authenticated
    USING ((SELECT auth.uid()) = user_id);

CREATE POLICY "Users can create their own release verifications"
    ON public.release_verifications
    FOR INSERT TO authenticated
    WITH CHECK ((SELECT auth.uid()) = user_id);

CREATE POLICY "Users can update their own release verifications"
    ON public.release_verifications
    FOR UPDATE TO authenticated
    USING ((SELECT auth.uid()) = user_id)
    WITH CHECK ((SELECT auth.uid()) = user_id);

ALTER TABLE public.check_results
    ADD COLUMN IF NOT EXISTS release_verification_id UUID
        REFERENCES public.release_verifications(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_check_results_release_verification
    ON public.check_results (release_verification_id, timestamp DESC)
    WHERE release_verification_id IS NOT NULL;
