from logging.config import dictConfig

from app.core.config import DevConfig, config

### skipped: logging to Logtail


def configure_logging() -> None:
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {
                "correlation_id": {
                    "()": "asgi_correlation_id.CorrelationIdFilter",
                    "uuid_length": 8 if isinstance(config, DevConfig) else 32,
                    "default_value": "-",
                },
            },
            "formatters": {
                "console": {
                    "class": "logging.Formatter",
                    "datefmt": "%Y:%m:%dT%H:%M:%S",
                    "format": "(%(correlation_id)s)  %(name)s:%(lineno)d - %(message)s",
                },
                "file": {
                    # "class": "logging.Formatter",
                    "class": "pythonjsonlogger.jsonlogger.JsonFormatter",  # for storing logs as json , (i.e: mostly for storing somewhere external)
                    "datefmt": "%Y:%m:%dT%H:%M:%S",
                    # "format": "%(asctime)s.%(msecs)0dZ | %(levelname)-8s | [%(correlation_id)s] %(name)s:%(lineno)d - %(message)s",
                    "format": "%(asctime)s.%(msecs)0dZ  %(levelname)-8s [%(correlation_id)s] %(name)s:%(lineno)d - %(message)s",  # with json
                },
            },
            "handlers": {
                "default": {
                    "class": "rich.logging.RichHandler",  # rich handler for nice logging.
                    "level": "DEBUG",
                    "formatter": "console",
                    "filters": ["correlation_id"],
                },
                "rotating_file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": "DEBUG",
                    "formatter": "file",
                    "filename": "app.log",
                    "maxBytes": 1024 * 1024,  # 1MB,
                    "backupCount": 2,  # keep only 2 log files
                    "encoding": "utf8",
                    "filters": ["correlation_id"],
                },
            },
            "loggers": {
                "uvicorn": {"handlers": ["default", "rotating_file"], "level": "INFO"},
                "app": {
                    "handlers": ["default", "rotating_file"],
                    "level": "DEBUG" if isinstance(config, DevConfig) else "INFO",
                    "propagate": False,
                },
                "database": {"handlers": ["default"], "level": "WARNING"},
                "aiosqlite": {"handlers": ["default"], "level": "WARNING"},
            },
        }
    )
