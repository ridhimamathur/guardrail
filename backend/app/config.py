from functools import lru_cache
import secrets

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    database_url: str = "postgresql+psycopg://CHANGE_ME:CHANGE_ME@localhost:5432/guardrail"

    # Process-only fallback keeps unit tests usable without a checked-in signing key.
    # Set these explicitly in .env for a stable local deployment.
    jwt_secret: str = secrets.token_urlsafe(48)
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480

    grant_hmac_secret: str = secrets.token_urlsafe(48)
    policy_version: str = "1.0.0"

    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    mailhog_smtp_host: str = "localhost"
    mailhog_smtp_port: int = 1025
    mailhog_api_url: str = "http://localhost:8025"

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "CHANGE_ME"
    minio_secret_key: str = "CHANGE_ME"
    minio_bucket: str = "finance-internal"
    minio_secure: bool = False

    github_token: str = ""
    github_owner: str = ""
    github_repo: str = ""
    github_enabled: bool = False

    demo_employee_password: str = "CHANGE_ME"
    demo_manager_password: str = "CHANGE_ME"
    demo_finance_password: str = "CHANGE_ME"
    demo_security_password: str = "CHANGE_ME"

    llm_provider: str = "mock"
    api_rate_limit: str = "120/minute"
    seed_on_startup: bool = True
    approval_expiry_minutes: int = 15
    action_expiry_minutes: int = 60
    synthetic_data_dir: str = "synthetic_data"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


def validate_local_configuration() -> Settings:
    """Reject template placeholders before starting the demo stack."""
    settings = get_settings()
    configured = {
        "DATABASE_URL": settings.database_url,
        "JWT_SECRET": settings.jwt_secret,
        "GRANT_HMAC_SECRET": settings.grant_hmac_secret,
        "MINIO_ACCESS_KEY": settings.minio_access_key,
        "MINIO_SECRET_KEY": settings.minio_secret_key,
        "DEMO_EMPLOYEE_PASSWORD": settings.demo_employee_password,
        "DEMO_MANAGER_PASSWORD": settings.demo_manager_password,
        "DEMO_FINANCE_PASSWORD": settings.demo_finance_password,
        "DEMO_SECURITY_PASSWORD": settings.demo_security_password,
    }
    missing = [name for name, value in configured.items() if not value or "CHANGE_ME" in value]
    if missing:
        names = ", ".join(missing)
        raise ValueError(f"Replace template values in local .env before startup: {names}")
    return settings
