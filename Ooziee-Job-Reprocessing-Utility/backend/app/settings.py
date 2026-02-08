from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List

class Settings(BaseSettings):
    db_url: str = Field(alias="DB_URL")
    jwt_secret: str = Field(alias="JWT_SECRET")
    jwt_expire_minutes: int = Field(default=720, alias="JWT_EXPIRE_MINUTES")

    redis_url: str = Field(default="redis://127.0.0.1:6379/0", alias="REDIS_URL")
    redis_channel: str = Field(default="oozie_reprocess_events", alias="REDIS_CHANNEL")

    cors_origins: str = Field(default="http://localhost:5173", alias="CORS_ORIGINS")

    oozie_default_url: str = Field(default="", alias="OOZIE_DEFAULT_URL")
    oozie_http_timeout: int = Field(default=30, alias="OOZIE_HTTP_TIMEOUT")

    bootstrap_admin_user: str = Field(default="admin", alias="BOOTSTRAP_ADMIN_USER")
    bootstrap_admin_pass: str = Field(default="admin123", alias="BOOTSTRAP_ADMIN_PASS")

    class Config:
        env_file = ".env"
        extra = "ignore"

    def cors_list(self) -> List[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

settings = Settings()
