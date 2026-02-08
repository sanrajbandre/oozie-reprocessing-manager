from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = Field(default="development", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    db_url: str = Field(default="sqlite:///./oozie_reprocess.db", alias="DB_URL")
    jwt_secret: str = Field(default="change-me-in-production", alias="JWT_SECRET")
    jwt_expire_minutes: int = Field(default=720, alias="JWT_EXPIRE_MINUTES")

    redis_url: str = Field(default="redis://127.0.0.1:6379/0", alias="REDIS_URL")
    redis_channel: str = Field(default="oozie_reprocess_events", alias="REDIS_CHANNEL")

    cors_origins: str = Field(default="http://localhost:5173", alias="CORS_ORIGINS")

    oozie_default_url: str = Field(default="", alias="OOZIE_DEFAULT_URL")
    oozie_http_timeout: int = Field(default=30, alias="OOZIE_HTTP_TIMEOUT")

    auto_create_schema: bool = Field(default=False, alias="AUTO_CREATE_SCHEMA")

    bootstrap_admin_enabled: bool = Field(default=False, alias="BOOTSTRAP_ADMIN_ENABLED")
    bootstrap_admin_user: str = Field(default="admin", alias="BOOTSTRAP_ADMIN_USER")
    bootstrap_admin_pass: Optional[str] = Field(default=None, alias="BOOTSTRAP_ADMIN_PASS")

    enforce_secure_defaults: bool = Field(default=False, alias="ENFORCE_SECURE_DEFAULTS")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    def cors_list(self) -> List[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

    def is_production(self) -> bool:
        return self.app_env.lower() in {"prod", "production"}

    def validate_runtime(self) -> None:
        secure_mode = self.enforce_secure_defaults or self.is_production()

        if self.jwt_expire_minutes < 5:
            raise RuntimeError("JWT_EXPIRE_MINUTES must be >= 5")

        db_url_lower = self.db_url.strip().lower()
        if db_url_lower.startswith("mysql"):
            if not db_url_lower.startswith("mysql+pymysql://"):
                raise RuntimeError("DB_URL for MySQL must use mysql+pymysql://")
            if "charset=utf8mb4" not in db_url_lower:
                raise RuntimeError("DB_URL for MySQL must include charset=utf8mb4")

        if secure_mode:
            if len(self.jwt_secret.strip()) < 24 or self.jwt_secret == "change-me-in-production":
                raise RuntimeError("JWT_SECRET is too weak for production mode")

        if self.bootstrap_admin_enabled:
            if not self.bootstrap_admin_pass:
                raise RuntimeError("BOOTSTRAP_ADMIN_PASS is required when BOOTSTRAP_ADMIN_ENABLED=true")
            if secure_mode and self.bootstrap_admin_pass == "admin123":
                raise RuntimeError("Default bootstrap admin password is not allowed in production mode")


settings = Settings()
