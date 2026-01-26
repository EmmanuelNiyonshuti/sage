from logging.config import dictConfig

from app.core.config import DevConfig, config


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
                    "style": "{",
                    "format": "({correlation_id})  {name}:{lineno:d} - {message}",
                },
                "file": {
                    "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
                    "datefmt": "%Y:%m:%dT%H:%M:%S",
                    "style": "{",
                    "format": "{asctime}.{msecs:0d}Z  {levelname:-8s} [{correlation_id}] {name}:{lineno:d} - {message}",
                },
            },
            "handlers": {
                "default": {
                    "class": "rich.logging.RichHandler",
                    "level": "DEBUG",
                    "formatter": "console",
                    "filters": ["correlation_id"],
                },
                "rotating_file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": "DEBUG",
                    "formatter": "file",
                    "filename": "logs/app.log",
                    "maxBytes": 1024 * 1024,  # 1MB,
                    "backupCount": 2,  # keep only 2 log files
                    "encoding": "utf8",
                    "filters": ["correlation_id"],
                },
            },
            "loggers": {
                "uvicorn": {
                    "handlers": ["default", "rotating_file"],
                    "level": "INFO",
                    "propagate": False,
                },
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
