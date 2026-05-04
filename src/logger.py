"""Loguru config and per-run directory bootstrap."""

import sys
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

from src.settings import Settings

_STDOUT_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> "
    "<level>{level: <8}</level> "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> "
    "- <level>{message}</level>"
)
_FILE_FORMAT = "{time:YYYY-MM-DDTHH:mm:ssZ} | {level: <8} | {name}:{function}:{line} | {message}"


def _utc_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")


def init_run(settings: Settings) -> Path:
    """Create a fresh per-run dir, attach loguru sinks, return the dir. Idempotent."""
    run_dir = settings.runs_dir / _utc_run_id()
    run_dir.mkdir(parents=True, exist_ok=True)

    logger.remove()
    logger.add(sys.stdout, level=settings.log_level, format=_STDOUT_FORMAT, colorize=True)
    logger.add(
        run_dir / "run.log",
        level=settings.log_level,
        format=_FILE_FORMAT,
        backtrace=False,
        diagnose=False,
    )

    return run_dir
