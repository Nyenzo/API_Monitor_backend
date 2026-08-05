from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import logging

from app.core.config import get_settings
from app.core.rate_limiter import limiter
from app.core.dependencies import init_supabase_clients, close_http_client
from app.api.v1.routers import auth, profiles, monitors, check_results, alerts, dashboard, internal

# Configure structured logging for the entire application
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("api_monitor")


# Lifespan context manager that initializes shared clients on startup and tears them down on shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    init_supabase_clients(settings)
    logger.info("API Monitor backend started")
    yield
    await close_http_client()
    logger.info("API Monitor backend stopped")


settings = get_settings()

# Create the main FastAPI application instance with OpenAPI metadata
app = FastAPI(
    title="API Monitor",
    description="API Monitor & Alerting System — track uptime, latency, and get instant alerts",
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Attach the rate limiter to the application state and register the error handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Allow the frontend origin to make cross-origin requests with credentials
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Internal-Key"],
)

# Register all v1 API routers under the /api/v1 prefix
app.include_router(auth.router, prefix="/api/v1")
app.include_router(profiles.router, prefix="/api/v1")
app.include_router(monitors.router, prefix="/api/v1")
app.include_router(check_results.router, prefix="/api/v1")
app.include_router(alerts.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(internal.router, prefix="/api/v1")


# Simple health-check endpoint for load balancers and Docker health probes
@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    return {"status": "healthy", "service": "api-monitor"}


# Catch-all handler that logs unhandled exceptions and returns a generic 500 response
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(f"Unhandled error on {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred"},
    )
