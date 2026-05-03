import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.domain import ConvFinQARecord
from src.repository.convfinqa import DatasetRepository, JsonDatasetRepository
from src.settings import Settings


@pytest.fixture(scope="module")
def repo() -> JsonDatasetRepository:
    return JsonDatasetRepository(Settings())


def test_load_train_returns_3037_records(repo: JsonDatasetRepository) -> None:
    records = repo.load_split("train")
    assert len(records) == 3037
    assert all(isinstance(r, ConvFinQARecord) for r in records)


def test_load_dev_returns_421_records(repo: JsonDatasetRepository) -> None:
    records = repo.load_split("dev")
    assert len(records) == 421
    assert all(isinstance(r, ConvFinQARecord) for r in records)


def test_load_test_split_raises_keyerror_naming_missing_split(
    repo: JsonDatasetRepository,
) -> None:
    with pytest.raises(KeyError) as excinfo:
        repo.load_split("test")
    assert "test" in str(excinfo.value)


def test_first_train_record_matches_known_values(repo: JsonDatasetRepository) -> None:
    first = repo.load_split("train")[0]
    assert first.id == "Single_JKHY/2009/page_28.pdf-3"
    assert first.dialogue.executed_answers == [206588.0, 181001.0, 25587.0, 0.14136]


def test_malformed_record_raises_validation_error(tmp_path: Path) -> None:
    fixture_path = tmp_path / "convfinqa_dataset.json"
    fixture_path.write_text(json.dumps({"train": [{"id": "x"}]}))

    repo = JsonDatasetRepository(Settings(data_dir=tmp_path))

    with pytest.raises(ValidationError):
        repo.load_split("train")


def test_repository_conforms_to_protocol() -> None:
    assert isinstance(JsonDatasetRepository(Settings()), DatasetRepository)
