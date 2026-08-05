from fastapi import APIRouter, Depends
from app.core.security import verify_internal_key
from app.tasks.health_checker import run_scheduled_checks

router = APIRouter(prefix="/internal", tags=["Internal"])


# Endpoint called by pg_cron every minute to trigger all due health checks
@router.post("/run-checks")
async def trigger_checks(
    _: bool = Depends(verify_internal_key),
) -> dict:
    result = await run_scheduled_checks()
    return result
