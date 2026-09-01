from fastapi import Depends, HTTPException, status, Request, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import Client
from app.core.config import get_settings, Settings
from app.core.dependencies import get_supabase_client, get_monitor_access_token, validate_monitor_api_key
from typing import Optional

# Extracts Bearer token from the Authorization header automatically without forcing it
security_scheme = HTTPBearer(auto_error=False)


# Dependency that validates the JWT with Supabase and returns the authenticated user
async def get_current_user(
    settings: Settings = Depends(get_settings),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    x_monitor_api_key: str | None = Header(default=None),
    supabase: Client = Depends(get_supabase_client),
) -> dict:
    try:
        if x_monitor_api_key is not None:
            validate_monitor_api_key(settings, x_monitor_api_key)
            token = await get_monitor_access_token(settings)
            response = supabase.auth.get_user(token)
            if not response or not response.user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Could not resolve monitoring service account.",
                )
            return {"id": response.user.id, "email": response.user.email, "token": token}
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated.",
            )
        # Ask Supabase to verify the token and return the user object
        response = supabase.auth.get_user(credentials.credentials)
        if not response or not response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )
        return {"id": response.user.id, "email": response.user.email, "token": credentials.credentials}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )


# Dependency that checks the X-Internal-Key header for server-to-server calls from pg_cron
async def verify_internal_key(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> bool:
    key = request.headers.get("X-Internal-Key", "")
    if not key or key != settings.internal_api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid internal API key",
        )
    return True
