from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "NEXUS"
    app_env: str = "development"
    app_debug: bool = True
    app_secret_key: str = "change-me-in-production"
    api_prefix: str = "/api/v1"

    jwt_secret: str = "change-me-jwt-secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480
    refresh_expire_days: int = 14

    database_url_env: Optional[str] = None
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "nexus"
    postgres_user: str = "nexus"
    postgres_password: str = "nexus"
    use_sqlite: bool = False
    sqlite_path: str = "/data/nexus.db"

    redis_url: str = "redis://localhost:6379/0"

    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "nexusminio"
    s3_secret_key: str = "nexusminio"
    s3_bucket: str = "nexus-raw"
    s3_region: str = "us-east-1"

    data_dir: str = "/data"
    max_upload_mb: int = 512
    cors_origins: str = "*"

    seed_on_startup: bool = True

    @property
    def database_url(self) -> str:
        import os

        explicit = os.environ.get("DATABASE_URL") or self.database_url_env
        if explicit:
            return explicit
        if self.use_sqlite:
            path = self.sqlite_path
            return f"sqlite:///{path}"
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def cors_origin_list(self) -> List[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
