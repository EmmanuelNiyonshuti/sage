from functools import lru_cache

from pydantic import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseConfig(BaseSettings):
    ENV_STATE: str | None = None
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class GlobalConfig(BaseConfig):
    DATABASE_URL: PostgresDsn
    DB_FORCE_ROLL_BACK: bool = False
    SENTINEL_HUB_BASE_URL: str | None = None
    SENTINEL_HUB_CLIENT_ID: str | None = None
    SENTINEL_HUB_CLIENT_SECRET: str | None = None
    ENABLE_SCHEDULER: bool = False
    INGESTION_SHEDULER_INTERVAL_DURATION: dict = {"hours": 24}
    TIMESERIES_SHEDULER_INTERVAL_DURATION: dict = {"hours": 24}


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
