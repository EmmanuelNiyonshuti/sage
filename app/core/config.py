from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseConfig(BaseSettings):
    ENV_STATE: str | None = None
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class GlobalConfig(BaseConfig):
    DATABASE_URL: str | None = None
    SENTINEL_HUB_BASE_URL: str | None = None
    SENTINEL_HUB_CLIENT_ID: str | None = None
    SENTINEL_HUB_CLIENT_SECRET: str | None = None
    ENABLE_SCHEDULER: bool | None = None
    SHEDULER_INTERVAL_HOURS: int | None = None


class DevConfig(GlobalConfig):
    model_config = SettingsConfigDict(env_prefix="DEV_")
    ENABLE_SCHEDULER: bool = True
    SHEDULER_INTERVAL_HOURS: int = 5  # placeholder


class TestConfig(GlobalConfig):
    DATABASE_URL: str = "sqlite:///:memory"
    model_config = SettingsConfigDict(env_prefix="TEST_")


class prodConfig(GlobalConfig):
    model_config = SettingsConfigDict(env_prefix="DEV_")


@lru_cache()
def get_config(env_state: str):
    config_dict = {"dev": DevConfig, "test": TestConfig, "prod": TestConfig}
    return config_dict[env_state]()


config = get_config(GlobalConfig().ENV_STATE)
