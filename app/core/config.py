from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseConfig(BaseSettings):
    ENV_STATE: str | None = None
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class GlobalConfig(BaseConfig):
    DATABASE_URL: str | None = "sqlite:///sg_dev.db"


class DevConfig(GlobalConfig):
    model_config = SettingsConfigDict(env_prefix="DEV_")


class TestConfig(GlobalConfig):
    DATABASE_URL: str = "sqlite:///sg_dev.db"
    model_config = SettingsConfigDict(env_prefix="TEST_")


class prodConfig(GlobalConfig):
    model_config = SettingsConfigDict(env_prefix="DEV_")


@lru_cache()
def get_config(env_state: str):
    config_dict = {"dev": DevConfig, "test": TestConfig, "prod": TestConfig}
    return config_dict[env_state]()


config = get_config(GlobalConfig().ENV_STATE)
