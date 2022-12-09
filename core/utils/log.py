import logging
import logging.handlers
import os
import sys

__all__ = ("setup_logging",)


def setup_logging():
    """Create and register default logging handlers."""

    # Create logging dir.
    log_dir = os.path.join(os.getcwd(), "logs")
    if not os.path.exists(log_dir):
        os.mkdir(log_dir)

    # Prepare loggers.
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    stream_handler = logging.StreamHandler(stream=sys.stdout)
    file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, "vibingway.log"),
        backupCount=7,
        encoding="utf-8",
    )

    fmt = "{asctime} | {levelname:<8} | {name}: {message}"
    date = "%d.%m.%Y %H:%M:%S"
    formatter = logging.Formatter(fmt, date, style="{")

    for handler in (stream_handler, file_handler):
        handler.setFormatter(formatter)
        root.addHandler(handler)

    # Reduce discord log output to errors only.
    discord_logger = logging.getLogger("discord")
    discord_logger.setLevel(logging.ERROR)

    
