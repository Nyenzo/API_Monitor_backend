from fastapi import APIRouter, Depends
from supabase import Client

from app.api.v1.routers.monitors import validate_monitor_target
from app.core.dependencies import get_authed_supabase
from app.core.security import get_current_user
from app.schemas.contract import ContractMonitorBatchCreate, ContractMonitorBatchResponse, OpenApiPreviewRequest, OpenApiPreviewResponse
from app.schemas.monitor import MonitorResponse
from app.services import monitor_service, openapi_service, product_metrics_service

router = APIRouter(prefix="/contracts", tags=["API Contracts"])


@router.post("/openapi/preview", response_model=OpenApiPreviewResponse)
async def preview_openapi(payload: OpenApiPreviewRequest, user: dict = Depends(get_current_user), supabase: Client = Depends(get_authed_supabase)) -> OpenApiPreviewResponse:
    title, operations = openapi_service.preview_openapi_document(payload.document)
    product_metrics_service.record_openapi_preview(supabase, user["id"])
    return OpenApiPreviewResponse(title=title, operations=operations)


@router.post("/monitors", response_model=ContractMonitorBatchResponse, status_code=201)
async def create_contract_monitors(payload: ContractMonitorBatchCreate, user: dict = Depends(get_current_user), supabase: Client = Depends(get_authed_supabase)) -> ContractMonitorBatchResponse:
    monitors = [
        monitor if monitor.monitor_kind == "contract" else monitor.model_copy(update={"monitor_kind": "contract"})
        for monitor in payload.monitors
    ]

    # Validate the complete request first so an unsafe target never leaves a partial import behind.
    for monitor in monitors:
        await validate_monitor_target(monitor.url)

    created = [
        MonitorResponse(**await monitor_service.create_monitor(supabase, user["id"], monitor))
        for monitor in monitors
    ]
    return ContractMonitorBatchResponse(monitors=created)
