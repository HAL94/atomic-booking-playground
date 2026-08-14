from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfigSettings(BaseSettings):
    ENV: str = "prod"
    APP_PORT: int = 8000
    HOST: str = "localhost"


class PostgresSettings(BaseSettings):
    PG_USER: str
    PG_PW: str
    PG_SERVER: str
    PG_PORT: str
    PG_DB: str


class JwtSettings(BaseSettings):
    JWT_SECRET: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    ALGORITHM: str = "HS256"


class RedisSettings(BaseSettings):
    REDIS_SERVER: str


class Settings(PostgresSettings, AppConfigSettings, RedisSettings, JwtSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()


def get_settings() -> Settings:
    global settings  # noqa: PLW0603
    if settings is None:
        settings = Settings()
    return settings
