from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "personalos-backend"
    environment: str = "development"
    port: int = 4000
    database_url: str = "sqlite:///./personalos.db"
    cors_origins: str = "*"
    seed_demo_data: bool = True
    demo_password: str
    jwt_secret: str = "change-this-development-secret-to-a-long-random-value"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
