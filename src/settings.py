"""Project settings loaded from environment / .env."""

from pathlib import Path
from typing import ClassVar

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class AnthropicSettings(BaseModel):
    api_key: str = ""
    model_name: str = "claude-sonnet-4-6"
    # Sonnet 4.6 list price (USD per million tokens) — used for cost
    # reporting in eval summaries. Override via env if pricing changes.
    price_per_mtok_input: float = 3.0
    price_per_mtok_output: float = 15.0

    # Extended thinking: off by default. When enabled the client switches
    # tool_choice from "tool" to "any" (forced single-tool isn't allowed
    # alongside thinking) and request max_tokens grows to budget + output cap.
    thinking_enabled: bool = False
    thinking_budget_tokens: int = 2048


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

    anthropic: AnthropicSettings = AnthropicSettings()
