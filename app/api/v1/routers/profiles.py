from fastapi import APIRouter, Depends
from supabase import Client
from app.core.dependencies import get_authed_supabase
from app.core.security import get_current_user
from app.schemas.profile import ProfileResponse, ProfileUpdate

router = APIRouter(prefix="/profiles", tags=["Profiles"])


# Fetch the authenticated user's profile data from the profiles table
@router.get("/me", response_model=ProfileResponse)
async def get_profile(
    user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_authed_supabase),
) -> ProfileResponse:
    response = (
        supabase.table("profiles")
        .select("*")
        .eq("id", user["id"])
        .single()
        .execute()
    )
    return ProfileResponse(**response.data)


# Update editable profile fields for the authenticated user
@router.patch("/me", response_model=ProfileResponse)
async def update_profile(
    payload: ProfileUpdate,
    user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_authed_supabase),
) -> ProfileResponse:
    data = payload.model_dump(exclude_none=True)
    response = (
        supabase.table("profiles")
        .update(data)
        .eq("id", user["id"])
        .execute()
    )
    return ProfileResponse(**response.data[0])
