import logging
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from app.core.config import config as app_config
from app.core.database import Base

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
logger = logging.getLogger("alembic.env")

# Validate DATABASE_URI before proceeding
try:
    db_url = app_config.DATABASE_URL
    if not db_url:
        raise ValueError("DATABASE_URI is not set in application configuration")

    config.set_main_option("sqlalchemy.url", db_url)
    logger.info("Database URL configured successfully")

except AttributeError as e:
    logger.error("DATABASE_URI attribute not found in app configuration")
    logger.error(f"Error details: {str(e)}", exc_info=True)
    sys.exit(1)
except ValueError as e:
    logger.error(f"Configuration Error: {str(e)}")
    sys.exit(1)
except Exception as e:
    logger.error(
        f"Unexpected error while configuring database: {str(e)}", exc_info=True
    )
    sys.exit(1)

# add your model's MetaData object here
# for 'autogenerate' support
from app.models import *  # noqa

# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def include_object(object, name, type_, reflected, compare_to):
    # Ignore PostGIS system tables
    if type_ == "table" and name == "spatial_ref_sys":  # might add more later.
        return False
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
