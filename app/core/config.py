from pydantic_settings import BaseSettings
from functools import lru_cache


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

    # SMTP settings used by the email alert sender
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "alerts@apexwatch.dev"

    # Application metadata surfaced in docs and health endpoint
    app_name: str = "ApexWatch"
    app_version: str = "1.0.0"
    debug: bool = False

    # Read from .env file at the project root
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # Split the comma-separated CORS string into a list for FastAPI middleware
    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


# Singleton cached settings instance so env is parsed once per process
@lru_cache
def get_settings() -> Settings:
    return Settings()
