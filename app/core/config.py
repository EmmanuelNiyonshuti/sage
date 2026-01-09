from functools import lru_cache

from pydantic import PostgresDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseConfig(BaseSettings):
    ENV_STATE: str | None = None
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class GlobalConfig(BaseConfig):
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_DB: str
    POSTGRES_PORT: int = 5433
    DB_FORCE_ROLL_BACK: bool = False
    SENTINEL_HUB_BASE_URL: str | None = None
    SENTINEL_HUB_CLIENT_ID: str | None = None
    SENTINEL_HUB_CLIENT_SECRET: str | None = None
    ENABLE_SCHEDULER: bool = False
    INGESTION_SHEDULER_INTERVAL_DURATION: dict = {"hours": 24}
    TIMESERIES_SHEDULER_INTERVAL_DURATION: dict = {"hours": 24}
    API_BASE_URL: str | None = "http://localhost:8000/api/v1"

    @computed_field
    @property
    def DATABASE_URL(self) -> PostgresDsn:
        return PostgresDsn.build(
            scheme="postgresql+psycopg2",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )


class DevConfig(GlobalConfig):
    model_config = SettingsConfigDict(env_prefix="DEV_")


class TestConfig(GlobalConfig):
    DB_FORCE_ROLL_BACK: bool = True
    ENABLE_SCHEDULER: bool = True
    model_config = SettingsConfigDict(env_prefix="TEST_")


class ProdConfig(GlobalConfig):
    ENABLE_SCHEDULER: bool = True
    model_config = SettingsConfigDict(env_prefix="PROD_")
    INGESTION_SHEDULER_INTERVAL_DURATION: dict = {"hours": 1}


@lru_cache()
def get_config(env_state: str):
    config_dict = {"dev": DevConfig, "test": TestConfig, "prod": ProdConfig}
    return config_dict[env_state]()


config = get_config(BaseConfig().ENV_STATE)
