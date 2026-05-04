"""Single entry point for reading the ConvFinQA dataset JSON."""

import json
from pathlib import Path
from typing import Protocol, runtime_checkable

from src.domain import ConvFinQARecord
from src.settings import Settings


@runtime_checkable
class DatasetRepository(Protocol):
    def load_split(self, split: str) -> list[ConvFinQARecord]: ...


class JsonDatasetRepository:
    def __init__(self, settings: Settings) -> None:
        self._path: Path = settings.data_dir / "convfinqa_dataset.json"

    def load_split(self, split: str) -> list[ConvFinQARecord]:
        # `split` is `str` not `Literal` so a "test" call reaches the body and
        # surfaces the withheld split as a runtime KeyError.
        with self._path.open("r", encoding="utf-8") as fh:
            payload = json.load(fh)

        if split not in payload:
            raise KeyError(
                f"split {split!r} not in dataset; available: {sorted(payload.keys())}"
            )

        return [ConvFinQARecord.model_validate(record) for record in payload[split]]
