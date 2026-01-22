"""
TaxonomyService for Smart-Agriculture system.

This module provides a singleton service that loads taxonomy_standard_v1.json
and provides fast in-memory lookups for taxonomy entries.
"""

from app.models.taxonomy import TaxonomyStandard, TaxonomyEntry, Metadata
from pathlib import Path
import json
from typing import Optional


class TaxonomyNotFoundError(Exception):
    """Raised when a taxonomy entry is not found."""

    pass


class TaxonomyService:
    """
    Singleton service for taxonomy lookups.

    This service loads taxonomy_standard_v1.json at startup
    and provides fast in-memory lookups.
    """

    _instance: Optional["TaxonomyService"] = None

    def __new__(cls) -> "TaxonomyService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        # Load JSON file
        json_path = Path("data/taxonomy_standard_v1.json")
        if not json_path.exists():
            raise FileNotFoundError(
                f"Taxonomy file not found at {json_path}. "
                "Please ensure data/taxonomy_standard_v1.json exists."
            )

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Validate with Pydantic
        self._data = TaxonomyStandard(**data)

        # Build indexes for fast lookup
        self._by_id: dict[int, TaxonomyEntry] = {
            entry.id: entry for entry in self._data.taxonomy
        }
        self._by_label: dict[str, TaxonomyEntry] = {
            entry.model_label: entry for entry in self._data.taxonomy
        }
        self._by_zh_name: dict[str, TaxonomyEntry] = {
            entry.zh_scientific_name: entry for entry in self._data.taxonomy
        }

    @property
    def metadata(self) -> Metadata:
        """Get taxonomy metadata."""
        return self._data.metadata

    def get_all(self) -> list[TaxonomyEntry]:
        """Get all taxonomy entries."""
        return self._data.taxonomy

    def get_by_id(self, id: int) -> TaxonomyEntry:
        """
        Get taxonomy entry by ID.

        Args:
            id: Taxonomy entry ID

        Returns:
            TaxonomyEntry

        Raises:
            TaxonomyNotFoundError: If ID not found
        """
        if id not in self._by_id:
            raise TaxonomyNotFoundError(f"Taxonomy ID {id} not found")
        return self._by_id[id]

    def get_by_model_label(self, label: str) -> TaxonomyEntry:
        """
        Get taxonomy entry by CV model label.

        Args:
            label: Model output label (e.g., 'spider_mite')

        Returns:
            TaxonomyEntry

        Raises:
            TaxonomyNotFoundError: If label not found
        """
        if label not in self._by_label:
            raise TaxonomyNotFoundError(f"Model label '{label}' not found")
        return self._by_label[label]

    def get_by_name(self, name: str) -> TaxonomyEntry:
        """
        Get taxonomy entry by Chinese scientific name.

        Args:
            name: Chinese scientific name

        Returns:
            TaxonomyEntry

        Raises:
            TaxonomyNotFoundError: If name not found
        """
        if name not in self._by_zh_name:
            raise TaxonomyNotFoundError(f"Chinese name '{name}' not found")
        return self._by_zh_name[name]

    def get_search_keywords(self, id: int) -> list[str]:
        """
        Get search keywords for RAG retrieval.

        Args:
            id: Taxonomy entry ID

        Returns:
            List of search keywords (empty list if not defined)

        Raises:
            TaxonomyNotFoundError: If ID not found
        """
        entry = self.get_by_id(id)
        return entry.search_keywords or []


# Module-level singleton instance
_taxonomy_service: Optional[TaxonomyService] = None


def get_taxonomy_service() -> TaxonomyService:
    """
    Get the singleton TaxonomyService instance.

    Returns:
        TaxonomyService instance
    """
    global _taxonomy_service
    if _taxonomy_service is None:
        _taxonomy_service = TaxonomyService()
    return _taxonomy_service
