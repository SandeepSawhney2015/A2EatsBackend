from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    apple_bundle_id: str = "MichiganMakers.A2Eats"
    database_url: str = ""
    jwt_secret: str = ""
    # Access tokens are short-lived; the Redis session (refresh token) keeps
    # the user signed in and is what actually defines "session length".
    jwt_expire_minutes: int = 15
    refresh_expire_days: int = 60
    redis_url: str = ""
    restaurant_secret_token: str = ""

    # S3-compatible photo storage. Works with AWS S3 (leave endpoint empty)
    # or Cloudflare R2 (set endpoint to your R2 URL). Credentials use the
    # standard AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY env vars.
    s3_bucket: str = ""
    s3_region: str = "us-east-2"
    s3_endpoint_url: str = ""
    s3_public_base_url: str = ""
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
