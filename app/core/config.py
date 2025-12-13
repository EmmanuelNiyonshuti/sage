from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseConfig(BaseSettings):
    ENV_STATE: str | None = None
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class GlobalConfig(BaseConfig):
    DATABASE_URL: str | None = None
    DB_FORCE_ROLL_BACK: bool = False
    SENTINEL_HUB_BASE_URL: str | None = None
    SENTINEL_HUB_CLIENT_ID: str | None = None
    SENTINEL_HUB_CLIENT_SECRET: str | None = None
    ENABLE_SCHEDULER: bool = False
    SHEDULER_INTERVAL_HOURS: int = 1


class DevConfig(GlobalConfig):
    model_config = SettingsConfigDict(env_prefix="DEV_")
    # ENABLE_SCHEDULER: bool = True
    SHEDULER_INTERVAL_HOURS: int = 24


class TestConfig(GlobalConfig):
    DATABASE_URL: str | None = None
    DB_FORCE_ROLL_BACK: bool = True
    model_config = SettingsConfigDict(env_prefix="TEST_")


class ProdConfig(GlobalConfig):
    DATABASE_URL: str | None = None
    ENABLE_SCHEDULER: bool = True
    model_config = SettingsConfigDict(env_prefix="PROD_")


@lru_cache()
def get_config(env_state: str):
    config_dict = {"dev": DevConfig, "test": TestConfig, "prod": ProdConfig}
    return config_dict[env_state]()


config = get_config(BaseConfig().ENV_STATE)
