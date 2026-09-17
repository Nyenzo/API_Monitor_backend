import httpx
from fastapi import APIRouter, Depends
from supabase import Client

from app.core.dependencies import get_authed_supabase, get_http_client, get_supabase_admin
from app.core.security import get_current_user
from app.schemas.release_verification import ReleaseVerificationCreate, ReleaseVerificationDetail, ReleaseVerificationResponse
from app.services import release_verification_service

router = APIRouter(prefix="/release-verifications", tags=["Release Verifications"])


@router.post("", response_model=ReleaseVerificationResponse, status_code=201)
async def create_release_verification(payload: ReleaseVerificationCreate, user: dict = Depends(get_current_user), supabase: Client = Depends(get_authed_supabase), supabase_admin: Client = Depends(get_supabase_admin), http_client: httpx.AsyncClient = Depends(get_http_client)) -> ReleaseVerificationResponse:
    run = await release_verification_service.run_release_verification(supabase, supabase_admin, http_client, user["id"], payload)
    return ReleaseVerificationResponse(**run)


@router.get("", response_model=list[ReleaseVerificationResponse])
async def list_release_verification_runs(user: dict = Depends(get_current_user), supabase: Client = Depends(get_authed_supabase)) -> list[ReleaseVerificationResponse]:
    return [ReleaseVerificationResponse(**run) for run in release_verification_service.list_release_verifications(supabase, user["id"])]


@router.get("/{run_id}", response_model=ReleaseVerificationDetail)
async def get_release_verification_run(run_id: str, user: dict = Depends(get_current_user), supabase: Client = Depends(get_authed_supabase)) -> ReleaseVerificationDetail:
    run, results = release_verification_service.get_release_verification(supabase, run_id, user["id"])
    return ReleaseVerificationDetail(**run, results=results)
