from fastapi import APIRouter, Depends
from app.core.dependencies import get_supabase_admin
from app.core.security import verify_internal_key
from app.schemas.product_metrics import ActivationMetricsResponse
from app.services import product_metrics_service
from supabase import Client
from app.tasks.health_checker import run_scheduled_checks

router = APIRouter(prefix="/internal", tags=["Internal"])


# Endpoint called by pg_cron every minute to trigger all due health checks
@router.post("/run-checks")
async def trigger_checks(
    _: bool = Depends(verify_internal_key),
) -> dict:
    result = await run_scheduled_checks()
    return result


@router.get("/activation-metrics", response_model=ActivationMetricsResponse)
async def get_activation_metrics(
    _: bool = Depends(verify_internal_key),
    supabase_admin: Client = Depends(get_supabase_admin),
) -> ActivationMetricsResponse:
    return ActivationMetricsResponse(**product_metrics_service.get_activation_metrics(supabase_admin))
