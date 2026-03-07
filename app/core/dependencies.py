from supabase import create_client, Client
from app.core.config import get_settings, Settings
from fastapi import Depends
import httpx

# Module-level singletons for shared clients
_supabase_client: Client | None = None
_supabase_admin: Client | None = None
_http_client: httpx.AsyncClient | None = None


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
