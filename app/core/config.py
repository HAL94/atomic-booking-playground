from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


class AppSettings(BaseConfig):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", env_prefix="APP_", extra="ignore")

    ENV: str = "prod"
    PORT: int = 8000
    HOST: str = "localhost"


class PostgresSettings(BaseConfig):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", env_prefix="PG_", extra="ignore")

    DB_USER: str
    DB_PW: str
    DB_SERVER: str
    DB_PORT: str
    DB_NAME: str


class JwtSettings(BaseConfig):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", env_prefix="SEC_", extra="ignore")

    JWT_SECRET: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    ALGORITHM: str = "HS256"


class RedisSettings(BaseConfig):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", env_prefix="REDIS_", extra="ignore")

    SERVER: str


class Settings:
    def __init__(self) -> None:
        self.app = AppSettings()
        self.postgres = PostgresSettings()
        self.jwt = JwtSettings()
        self.redis = RedisSettings()

    @property
    def ENV(self) -> str:
        return self.app.ENV

    @property
    def HOST(self) -> str:
        return self.app.HOST

    @property
    def PORT(self) -> int:
        return self.app.PORT

    @property
    def APP_PORT(self) -> int:
        return self.app.PORT

    @property
    def DB_USER(self) -> str:
        return self.postgres.DB_USER

    @property
    def DB_PW(self) -> str:
        return self.postgres.DB_PW

    @property
    def DB_SERVER(self) -> str:
        return self.postgres.DB_SERVER

    @property
    def DB_PORT(self) -> str:
        return self.postgres.DB_PORT

    @property
    def DB_NAME(self) -> str:
        return self.postgres.DB_NAME

    @property
    def PG_USER(self) -> str:
        return self.DB_USER

    @property
    def PG_PW(self) -> str:
        return self.DB_PW

    @property
    def PG_SERVER(self) -> str:
        return self.DB_SERVER

    @property
    def PG_PORT(self) -> str:
        return self.DB_PORT

    @property
    def PG_DB(self) -> str:
        return self.DB_NAME

    @property
    def REDIS_SERVER(self) -> str:
        return self.redis.SERVER

    @property
    def JWT_SECRET(self) -> str:
        return self.jwt.JWT_SECRET

    @property
    def ACCESS_TOKEN_EXPIRE_MINUTES(self) -> int:
        return self.jwt.ACCESS_TOKEN_EXPIRE_MINUTES

    @property
    def REFRESH_TOKEN_EXPIRE_MINUTES(self) -> int:
        return self.jwt.REFRESH_TOKEN_EXPIRE_MINUTES

    @property
    def ALGORITHM(self) -> str:
        return self.jwt.ALGORITHM


settings = Settings()


def get_settings() -> Settings:
    return settings
