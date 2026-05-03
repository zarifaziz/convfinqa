"""Project settings loaded from environment / .env."""

from pathlib import Path
from typing import ClassVar

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_nested_delimiter="__",
    )

    project_root: ClassVar[Path] = Path(__file__).resolve().parent.parent

    data_dir: Path = project_root / "data"
    runs_dir: Path = project_root / "runs"

    # Metric uses max(tol_abs, tol_rel * |gold|): abs covers near-zero, rel covers display-rounded percents.
    tol_abs: float = 1e-4
    tol_rel: float = 5e-3

    log_level: str = "INFO"
