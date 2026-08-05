from fastapi import APIRouter, Depends, Request
from supabase import Client
from app.core.dependencies import get_supabase_client
from app.core.security import get_current_user
from app.core.rate_limiter import limiter
from app.schemas.auth import SignupRequest, LoginRequest, AuthResponse, RefreshRequest, UserInfo
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


# Create a new account with rate limiting to prevent abuse
@router.post("/signup", response_model=AuthResponse)
@limiter.limit("5/minute")
async def signup(
    request: Request,
    payload: SignupRequest,
    supabase: Client = Depends(get_supabase_client),
) -> AuthResponse:
    return await auth_service.signup_user(supabase, payload)


# Authenticate with email and password, rate limited to 10 attempts per minute
@router.post("/login", response_model=AuthResponse)
@limiter.limit("10/minute")
async def login(
    request: Request,
    payload: LoginRequest,
    supabase: Client = Depends(get_supabase_client),
) -> AuthResponse:
    return await auth_service.login_user(supabase, payload)


# Invalidate the current session for the authenticated user
@router.post("/logout")
async def logout(
    request: Request,
    supabase: Client = Depends(get_supabase_client),
    user: dict = Depends(get_current_user),
) -> dict:
    await auth_service.logout_user(supabase)
    return {"message": "Logged out successfully"}


# Exchange a refresh token for a new access token pair
@router.post("/refresh", response_model=AuthResponse)
async def refresh(
    request: Request,
    payload: RefreshRequest,
    supabase: Client = Depends(get_supabase_client),
) -> AuthResponse:
    return await auth_service.refresh_session(supabase, payload)


# Return the identity of the currently authenticated user
@router.get("/me", response_model=UserInfo)
async def me(user: dict = Depends(get_current_user)) -> UserInfo:
    return UserInfo(id=user["id"], email=user["email"])
