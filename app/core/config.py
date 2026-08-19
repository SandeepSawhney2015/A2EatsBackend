from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    apple_bundle_id: str = "MichiganMakers.A2Eats"
    database_url: str = ""
    jwt_secret: str = ""
    # Access tokens are short-lived; the Redis session (refresh token) keeps
    # the user signed in and is what actually defines "session length".
    jwt_expire_minutes: int = 15
    refresh_expire_days: int = 60
    redis_url: str = "redis://localhost:6379/0"


@lru_cache
def get_settings() -> Settings:
    return Settings()
