from supabase import create_client, Client
from app.core.config import get_settings, Settings
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Used by get_authed_supabase to extract the Bearer token without raising on missing auth
_bearer = HTTPBearer(auto_error=False)

# Module-level singletons for shared clients
_supabase_client: Client | None = None
_supabase_admin: Client | None = None
_http_client: httpx.AsyncClient | None = None

# Cached monitoring service account session
# Stores the access token and its expiry time so we sign in once and reuse the token
_monitor_access_token: str | None = None
_monitor_token_expires_at: float = 0.0  # unix timestamp


async def _get_monitor_token(settings: Settings) -> str:
    """Sign in as the monitoring service account and cache the JWT.
    Refreshes automatically when the token is within 60 seconds of expiry.
    """
    global _monitor_access_token, _monitor_token_expires_at
    if _monitor_access_token and time.time() < _monitor_token_expires_at - 60:
        return _monitor_access_token
    if not settings.monitor_email or not settings.monitor_password:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Monitoring service account not configured on this server.",
        )
    client = create_client(settings.supabase_url, settings.supabase_anon_key)
    response = client.auth.sign_in_with_password(
        {"email": settings.monitor_email, "password": settings.monitor_password}
    )
    session = response.session
    if not session:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not authenticate monitoring service account.",
        )
    _monitor_access_token = session.access_token
    _monitor_token_expires_at = time.time() + session.expires_in
    logger.info("Monitoring service account token refreshed.")
    if not _monitor_access_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Monitoring service account returned an empty token.",
        )
    return _monitor_access_token


# Returns the anon-key Supabase client that respects row-level security
def get_supabase_client(settings: Settings = Depends(get_settings)) -> Client:
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = create_client(settings.supabase_url, settings.supabase_anon_key)
    return _supabase_client


# Returns the service-role Supabase client that bypasses row-level security
def get_supabase_admin(settings: Settings = Depends(get_settings)) -> Client:
    global _supabase_admin
    if _supabase_admin is None:
        _supabase_admin = create_client(settings.supabase_url, settings.supabase_service_role_key)
    return _supabase_admin


# Per-request Supabase client authenticated as the calling user.
#
# Accepts two forms of authentication:
#   1. Authorization: Bearer <user-jwt>  — normal interactive user requests
#   2. X-Monitor-Api-Key: <secret>       — long-running monitor checks that use
#      the dedicated monitoring service account so the token never expires.
async def get_authed_supabase(
    settings: Settings = Depends(get_settings),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    x_monitor_api_key: Optional[str] = Header(default=None),
) -> Client:
    # --- Monitoring service account path ---
    if x_monitor_api_key is not None:
        if not settings.monitor_api_key or x_monitor_api_key != settings.monitor_api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid monitor API key.",
            )
        token = await _get_monitor_token(settings)
        client = create_client(settings.supabase_url, settings.supabase_anon_key)
        client.postgrest.auth(token)
        return client

    # --- Normal user JWT path ---
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
        )
    client = create_client(settings.supabase_url, settings.supabase_anon_key)
    client.postgrest.auth(credentials.credentials)
    return client


# Returns a shared async HTTP client with connection pooling for health-check requests
async def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=5.0),
            follow_redirects=True,
            limits=httpx.Limits(max_connections=500, max_keepalive_connections=100),
        )
    return _http_client


# Gracefully shuts down the HTTP client when the application stops
async def close_http_client() -> None:
    global _http_client
    if _http_client and not _http_client.is_closed:
        await _http_client.aclose()
        _http_client = None


# Eagerly creates both Supabase clients during application startup
def init_supabase_clients(settings: Settings) -> None:
    global _supabase_client, _supabase_admin
    _supabase_client = create_client(settings.supabase_url, settings.supabase_anon_key)
    _supabase_admin = create_client(settings.supabase_url, settings.supabase_service_role_key)
