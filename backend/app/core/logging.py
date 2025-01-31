import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from loguru import logger
from .config import settings

# Create logs directory if it doesn't exist
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

# Configure loguru logger
config: Dict[str, Any] = {
    "handlers": [
        {
            "sink": sys.stdout,
            "format": "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            "level": "INFO",
        },
        {
            "sink": LOGS_DIR / f"app_{datetime.now().strftime('%Y%m%d')}.log",
            "format": "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            "level": "DEBUG",
            "rotation": "00:00",  # Create new file at midnight
            "retention": "30 days",  # Keep logs for 30 days
            "compression": "zip",  # Compress rotated files
        }
    ],
}

# Remove default logger
logger.remove()

# Add configured handlers
for handler in config["handlers"]:
    logger.add(**handler)

# Intercept standard library logging
class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )

# Setup standard library logging to use loguru
logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

# Setup uvicorn logging to use loguru
logging.getLogger("uvicorn.access").handlers = [InterceptHandler()]
logging.getLogger("uvicorn.error").handlers = [InterceptHandler()]

# Create logger instance for import
app_logger = logger.bind(service="objectdms") 