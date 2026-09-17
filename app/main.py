from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import logging

from app.core.config import get_settings
from app.core.rate_limiter import limiter
from app.core.dependencies import init_supabase_clients, close_http_client
from app.api.v1.routers import auth, profiles, monitors, check_results, alerts, contracts, dashboard, internal, release_verifications

# Configure structured logging for the entire application
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("api_monitor")


# Lifespan context manager that initializes shared clients on startup and tears them down on shutdown
@asynccontextmanager
async def lifespan(_: FastAPI):
    runtime_settings = get_settings()
    init_supabase_clients(runtime_settings)
    logger.info("API Monitor backend started")
    yield
    await close_http_client()
    logger.info("API Monitor backend stopped")


app_settings = get_settings()

# Create the main FastAPI application instance with OpenAPI metadata
app = FastAPI(
    title="API Monitor",
    description="API Monitor & Alerting System — track uptime, latency, and get instant alerts",
    version=app_settings.app_version,
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
    allow_origins=app_settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Internal-Key", "X-Monitor-Api-Key"],
)

# Register all v1 API routers under the /api/v1 prefix
app.include_router(auth.router, prefix="/api/v1")
app.include_router(profiles.router, prefix="/api/v1")
app.include_router(monitors.router, prefix="/api/v1")
app.include_router(check_results.router, prefix="/api/v1")
app.include_router(alerts.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(internal.router, prefix="/api/v1")
app.include_router(contracts.router, prefix="/api/v1")
app.include_router(release_verifications.router, prefix="/api/v1")


def apply_cors_headers(request: Request, response: Response) -> Response:
    origin = request.headers.get("origin")
    if origin and origin in app_settings.cors_origin_list:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Vary"] = "Origin"
    return response


@app.exception_handler(HTTPException)
async def http_exception_with_cors(request: Request, exc: HTTPException) -> Response:
    response = await http_exception_handler(request, exc)
    return apply_cors_headers(request, response)


# Simple health-check endpoint for load balancers and Docker health probes
@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    return {"status": "healthy", "service": "api-monitor"}


# Catch-all handler that logs unhandled exceptions and returns a generic 500 response
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled error on %s %s: %s", request.method, request.url.path, exc)
    response = JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred"},
    )
    return apply_cors_headers(request, response)
