from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    supabase_url: str
    supabase_service_role_key: str
    supabase_db_url: str
    redis_url: str
    gemini_api_key: str
    sentry_dsn_backend: str | None = None
    frontend_origin: str = "http://localhost:3000"


settings = Settings()
