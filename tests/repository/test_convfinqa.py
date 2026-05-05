import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.repository.convfinqa import JsonDatasetRepository
from src.settings import Settings


def test_load_test_split_raises_keyerror_naming_missing_split() -> None:
    repo = JsonDatasetRepository(Settings())
    with pytest.raises(KeyError) as excinfo:
        repo.load_split("test")
    assert "test" in str(excinfo.value)


def test_malformed_record_raises_validation_error(tmp_path: Path) -> None:
    fixture_path = tmp_path / "convfinqa_dataset.json"
    fixture_path.write_text(json.dumps({"train": [{"id": "x"}]}))

    repo = JsonDatasetRepository(Settings(data_dir=tmp_path))

    with pytest.raises(ValidationError):
        repo.load_split("train")
