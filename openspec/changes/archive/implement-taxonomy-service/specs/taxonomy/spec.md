# Specification: Taxonomy Data Model

**Capability**: Taxonomy
**Version**: 1.0.0
**Status**: Proposed

---

## ADDED Requirements

### REQ-TAXONOMY-001: Pydantic Data Models

The system MUST define Pydantic models in `app/models/taxonomy.py` that match the JSON structure of `data/taxonomy_standard_v1.json`.

**Model Structure**:

```python
from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class Metadata(BaseModel):
    """Metadata for the taxonomy standard."""
    version: str = Field(..., description="Version of the taxonomy standard")
    last_updated: str = Field(..., description="Last update date (YYYY-MM-DD)")
    description: str = Field(..., description="Description of the taxonomy")
    maintainer: str = Field(..., description="Team maintaining the standard")

class TaxonomyEntry(BaseModel):
    """Single taxonomy entry for a pest or disease."""
    id: int = Field(..., description="Unique identifier (0-1000)")
    model_label: str = Field(..., description="CV model output label (e.g., 'spider_mite')")
    zh_scientific_name: str = Field(..., description="Chinese scientific name")
    latin_name: str = Field(..., description="Latin/scientific name")
    category: Literal["Pest", "Disease", "Status", "Anomaly"] = Field(
        ..., description="Category of the entry"
    )
    action_policy: Literal["PASS", "RETRIEVE", "HUMAN_REVIEW"] = Field(
        ..., description="Action policy for diagnosis"
    )
    search_keywords: Optional[List[str]] = Field(
        default=None, description="Keywords for RAG retrieval"
    )
    description: Optional[str] = Field(
        default=None, description="Additional description"
    )
    risk_level: Optional[str] = Field(
        default=None, description="Risk level (e.g., 'High', 'Medium')"
    )
    note: Optional[str] = Field(
        default=None, description="Additional notes"
    )

class TaxonomyStandard(BaseModel):
    """Complete taxonomy standard loaded from JSON."""
    metadata: Metadata
    taxonomy: List[TaxonomyEntry]
```

**Validation Rules**:
- `id` MUST be unique across all entries
- `model_label` MUST be non-empty and lowercase with underscores
- `category` MUST be one of: "Pest", "Disease", "Status", "Anomaly"
- `action_policy` MUST be one of: "PASS", "RETRIEVE", "HUMAN_REVIEW"

---

### REQ-TAXONOMY-002: TaxonomyService Singleton

The system MUST implement a singleton service in `app/services/taxonomy_service.py` that loads and manages the taxonomy data.

**Class Design**:

```python
from app.models.taxonomy import TaxonomyStandard, TaxonomyEntry
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

    def get_all(self) -> List[TaxonomyEntry]:
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

    def get_search_keywords(self, id: int) -> List[str]:
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
```

**Constraints**:
- MUST be thread-safe for read operations
- MUST cache data in memory after first load
- MUST NOT modify taxonomy data after initialization
- MUST fail-fast if JSON file is missing or invalid

---

### REQ-TAXONOMY-003: FastAPI Dependency Injection

The system MUST provide a FastAPI dependency injection function in `app/core/deps.py`.

**Implementation**:

```python
from fastapi import Depends
from app.services.taxonomy_service import TaxonomyService, get_taxonomy_service

async def depends_taxonomy(
    service: TaxonomyService = Depends(get_taxonomy_service)
) -> TaxonomyService:
    """
    FastAPI dependency injection for TaxonomyService.

    Usage in routes:
        @app.get("/diagnosis/{id}")
        async def get_diagnosis(
            id: int,
            taxonomy: TaxonomyService = Depends(depends_taxonomy)
        ):
            entry = taxonomy.get_by_id(id)
            return {"name": entry.zh_scientific_name}
    """
    return service
```

---

### REQ-TAXONOMY-004: Unit Testing

The system MUST include comprehensive unit tests in `tests/services/test_taxonomy.py`.

**Test Coverage**:

#### Scenario: Load Taxonomy Successfully
**GIVEN** a valid `taxonomy_standard_v1.json` file
**WHEN** TaxonomyService is initialized
**THEN** service loads without errors
**AND** metadata contains correct version
**AND** all 5 entries are loaded

#### Scenario: Get Entry by ID
**GIVEN** TaxonomyService is initialized
**WHEN** calling `get_by_id(3)`
**THEN** returns TaxonomyEntry for "叶螨" (spider_mite)
**AND** id equals 3
**AND** category equals "Pest"

#### Scenario: Get Entry by Model Label
**GIVEN** TaxonomyService is initialized
**WHEN** calling `get_by_model_label("aphid_complex")`
**THEN** returns TaxonomyEntry for "蚜虫类"
**AND** model_label equals "aphid_complex"

#### Scenario: Get Entry by Chinese Name
**GIVEN** TaxonomyService is initialized
**WHEN** calling `get_by_name("白粉病")`
**THEN** returns TaxonomyEntry for id=2
**AND** zh_scientific_name equals "白粉病"

#### Scenario: Get Search Keywords
**GIVEN** TaxonomyService is initialized
**WHEN** calling `get_search_keywords(3)`
**THEN** returns `["红蜘蛛", "二斑叶螨"]`

#### Scenario: Invalid ID Raises Error
**GIVEN** TaxonomyService is initialized
**WHEN** calling `get_by_id(999)`
**THEN** raises `TaxonomyNotFoundError`
**AND** error message contains "Taxonomy ID 999 not found"

#### Scenario: Missing JSON File
**GIVEN** JSON file does not exist
**WHEN** TaxonomyService is initialized
**THEN** raises `FileNotFoundError`
**AND** error message contains "Taxonomy file not found"

**Implementation**:

```python
import pytest
from app.services.taxonomy_service import TaxonomyService, TaxonomyNotFoundError, get_taxonomy_service

def test_load_taxonomy_success():
    """Test that taxonomy loads successfully."""
    service = TaxonomyService()
    assert service.metadata.version == "1.0.0"
    assert len(service.get_all()) == 5

def test_get_by_id():
    """Test getting entry by ID."""
    service = TaxonomyService()
    entry = service.get_by_id(3)
    assert entry.id == 3
    assert entry.model_label == "spider_mite"
    assert entry.zh_scientific_name == "叶螨"
    assert entry.category == "Pest"

def test_get_by_model_label():
    """Test getting entry by model label."""
    service = TaxonomyService()
    entry = service.get_by_model_label("aphid_complex")
    assert entry.id == 1
    assert entry.zh_scientific_name == "蚜虫类"

def test_get_by_name():
    """Test getting entry by Chinese name."""
    service = TaxonomyService()
    entry = service.get_by_name("白粉病")
    assert entry.id == 2

def test_get_search_keywords():
    """Test getting search keywords."""
    service = TaxonomyService()
    keywords = service.get_search_keywords(3)
    assert keywords == ["红蜘蛛", "二斑叶螨"]

def test_invalid_id_raises_error():
    """Test that invalid ID raises error."""
    service = TaxonomyService()
    with pytest.raises(TaxonomyNotFoundError) as exc_info:
        service.get_by_id(999)
    assert "Taxonomy ID 999 not found" in str(exc_info.value)

def test_singleton_pattern():
    """Test that service is a singleton."""
    service1 = TaxonomyService()
    service2 = TaxonomyService()
    assert service1 is service2

def test_get_taxonomy_service():
    """Test module-level factory function."""
    service = get_taxonomy_service()
    assert isinstance(service, TaxonomyService)
```

---

## MODIFIED Requirements

None (this is a new capability)

---

## DEPRECATED Requirements

None
