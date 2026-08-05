from supabase import Client
from app.schemas.auth import SignupRequest, LoginRequest, AuthResponse, RefreshRequest
from fastapi import HTTPException, status
from gotrue.errors import AuthApiError


# Register a new user through Supabase Auth and return tokens
async def signup_user(supabase: Client, payload: SignupRequest) -> AuthResponse:
    try:
        response = supabase.auth.sign_up({
            "email": payload.email,
            "password": payload.password,
            "options": {"data": {"full_name": payload.full_name}},
        })
        if not response.user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Signup failed")
        return AuthResponse(
            access_token=response.session.access_token if response.session else "",
            refresh_token=response.session.refresh_token if response.session else "",
            user_id=response.user.id,
            email=response.user.email or payload.email,
        )
    except HTTPException:
        raise
    except AuthApiError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


# Authenticate an existing user with email and password and return tokens
async def login_user(supabase: Client, payload: LoginRequest) -> AuthResponse:
    try:
        response = supabase.auth.sign_in_with_password({
            "email": payload.email,
            "password": payload.password,
        })
        if not response.user or not response.session:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        return AuthResponse(
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            user_id=response.user.id,
            email=response.user.email or payload.email,
        )
    except HTTPException:
        raise
    except AuthApiError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


# Exchange a refresh token for a new access/refresh token pair
async def refresh_session(supabase: Client, payload: RefreshRequest) -> AuthResponse:
    try:
        response = supabase.auth.refresh_session(payload.refresh_token)
        if not response.user or not response.session:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh failed")
        return AuthResponse(
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            user_id=response.user.id,
            email=response.user.email or "",
        )
    except HTTPException:
        raise
    except AuthApiError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


# Invalidate the current session on the server side
async def logout_user(supabase: Client) -> None:
    try:
        supabase.auth.sign_out()
    except AuthApiError:
        pass
