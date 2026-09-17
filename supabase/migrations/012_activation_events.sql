CREATE TABLE public.product_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL CHECK (event_type IN ('openapi_previewed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_product_events_type_created_user
    ON public.product_events (event_type, created_at DESC, user_id);

ALTER TABLE public.product_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own product events"
    ON public.product_events
    FOR SELECT TO authenticated
    USING ((SELECT auth.uid()) = user_id);

CREATE POLICY "Users can create their own product events"
    ON public.product_events
    FOR INSERT TO authenticated
    WITH CHECK ((SELECT auth.uid()) = user_id);
