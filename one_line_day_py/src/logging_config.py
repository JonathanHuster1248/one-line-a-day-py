from litestar.logging import LoggingConfig
from litestar.middleware.logging import LoggingMiddlewareConfig

from .settings import settings

# Request/response bodies can contain passwords (auth) or private journal entries,
# so only path/method/status are logged, never headers/cookies/query/body.
logging_middleware_config = LoggingMiddlewareConfig(
    exclude=["^/schema", "^/favicon\\.ico$", "^/ping$"],
    request_log_fields=["path", "method"],
    response_log_fields=["status_code"],
)

IMAGE_LIBRARY_LOGGERS = ("PIL", "pillow_heif")


def create_logging_config() -> LoggingConfig:
    log_dir = settings.db_path.parent / ".logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    return LoggingConfig(
        formatters={
            "standard": {
                "format": "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
            }
        },
        handlers={
            "console": {
                "class": "logging.StreamHandler",
                "level": settings.log_level,
                "formatter": "standard",
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": settings.log_level,
                "formatter": "standard",
                "filename": str(log_dir / "app.log"),
                "maxBytes": 10 * 1024 * 1024,
                "backupCount": 5,
            },
            "queue_listener": {
                "class": "logging.handlers.QueueHandler",
                "queue": {"()": "queue.Queue", "maxsize": -1},
                "listener": "litestar.logging.standard.LoggingQueueListener",
                "handlers": ["console", "file"],
            },
        },
        loggers={
            "litestar": {
                "level": settings.log_level,
                "handlers": ["queue_listener"],
                "propagate": False,
            },
            # At DEBUG, Pillow logs every EXIF tag it parses (camera, timestamps,
            # GPS), so its loggers stay at WARNING whatever LOG_LEVEL is.
            **{name: {"level": "WARNING"} for name in IMAGE_LIBRARY_LOGGERS},
        },
        root={"level": settings.log_level, "handlers": ["queue_listener"]},
    )
