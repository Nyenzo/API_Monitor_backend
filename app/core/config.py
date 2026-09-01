from functools import lru_cache
from pydantic import field_validator
from pydantic_settings import BaseSettings


# Central configuration loaded from environment variables via pydantic-settings
class Settings(BaseSettings):
    # Supabase connection credentials
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str

    # Shared secret that pg_cron includes when calling the internal endpoint
    internal_api_key: str

    # Comma-separated list of allowed CORS origins
    cors_origins: str = "http://localhost:5173"

    # Maximum API requests per minute per client IP
    rate_limit_per_minute: int = 60

    # Default timeouts and concurrency for health-check execution
    default_timeout_ms: int = 10000
    max_concurrent_checks: int = 200
    max_checks_per_run: int = 500

    # SMTP settings for email alert notifications (optional — alerts are skipped if smtp_host is empty)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "alerts@example.com"

    # Dedicated monitoring service account — used for long-running self-checks
    # without relying on a user JWT that expires every hour.
    # MONITOR_API_KEY   — random secret your monitor stores in its Headers field
    # MONITOR_EMAIL     — email of the service account created in Supabase Auth
    # MONITOR_PASSWORD  — password of that account
    monitor_api_key: str = ""
    monitor_email: str = ""
    monitor_password: str = ""

    # Application metadata surfaced in docs and health endpoint
    app_name: str = "API Monitor"
    app_version: str = "1.0.0"
    debug: bool = False

    # Read from .env file at the project root
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    # Accept common deployment mode strings so production envs do not crash startup
    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, value: bool | str) -> bool | str:
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on", "debug", "development", "dev"}:
                return True
            if normalized in {"0", "false", "no", "off", "release", "production", "prod"}:
                return False
        return value

    # Split the comma-separated CORS string into a list for FastAPI middleware
    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


# Singleton cached settings instance so env is parsed once per process
@lru_cache
def get_settings() -> Settings:
    return Settings()
