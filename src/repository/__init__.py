"""Repository layer: hides storage details behind Protocols."""

from src.repository.convfinqa import DatasetRepository, JsonDatasetRepository

__all__ = ["DatasetRepository", "JsonDatasetRepository"]
