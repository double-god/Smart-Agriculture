"""
Unit tests for TaxonomyService.

Tests cover loading, querying, error handling, and singleton behavior.
"""

from unittest.mock import mock_open, patch

import pytest

from app.services.taxonomy_service import (
    TaxonomyNotFoundError,
    TaxonomyService,
    TaxonomyValidationError,
    get_taxonomy_service,
)


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the singleton instance before and after each test."""
    TaxonomyService._instance = None
    yield
    TaxonomyService._instance = None



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


def test_invalid_label_raises_error():
    """Test that invalid model label raises error."""
    service = TaxonomyService()
    with pytest.raises(TaxonomyNotFoundError) as exc_info:
        service.get_by_model_label("invalid_label")
    assert "Model label 'invalid_label' not found" in str(exc_info.value)


def test_invalid_name_raises_error():
    """Test that invalid Chinese name raises error."""
    service = TaxonomyService()
    with pytest.raises(TaxonomyNotFoundError) as exc_info:
        service.get_by_name("不存在的病害")
    assert "Chinese name '不存在的病害' not found" in str(exc_info.value)


def test_search_keywords_empty_when_none():
    """Test that search keywords returns empty list when None."""
    service = TaxonomyService()
    # Entry with id=0 (healthy) has no search_keywords
    keywords = service.get_search_keywords(0)
    assert keywords == []

# --- Validation Tests ---

VALID_METADATA = {
    "version": "1.0.0",
    "last_updated": "2023-10-27",
    "description": "Test Taxonomy",
    "maintainer": "Test Team"
}

def test_validation_negative_id():
    """Test that negative ID raises validation error."""
    bad_data = {
        "metadata": VALID_METADATA,
        "taxonomy": [
            {
                "id": -1,
                "model_label": "pest_1",
                "zh_scientific_name": "害虫1",
                "latin_name": "Pestus oneus",
                "category": "Pest",
                "action_policy": "PASS"
            }
        ]
    }

    # We patch Path.exists to force it to try opening the file
    # We patch open/json.load to return our bad data
    with patch("pathlib.Path.exists", return_value=True), \
         patch("builtins.open", mock_open()), \
         patch("json.load", return_value=bad_data):

        with pytest.raises(TaxonomyValidationError) as exc:
            TaxonomyService()

        msg = str(exc.value)
        # Pydantic v2 error message for ge/gt
        assert "Input should be greater than or equal to 0" in msg


def test_validation_invalid_action_policy():
    """Test that invalid action_policy raises validation error."""
    bad_data = {
        "metadata": VALID_METADATA,
        "taxonomy": [
            {
                "id": 1,
                "model_label": "pest_1",
                "zh_scientific_name": "害虫1",
                "latin_name": "Pestus oneus",
                "category": "Pest",
                "action_policy": "DESTROY"  # Invalid
            }
        ]
    }

    with patch("pathlib.Path.exists", return_value=True), \
         patch("builtins.open", mock_open()), \
         patch("json.load", return_value=bad_data):

        with pytest.raises(TaxonomyValidationError) as exc:
            TaxonomyService()

        msg = str(exc.value)
        assert "Input should be 'PASS', 'RETRIEVE' or 'HUMAN_REVIEW'" in msg


def test_validation_missing_field():
    """Test that missing required field raises validation error."""
    bad_data = {
        "metadata": VALID_METADATA,
        "taxonomy": [
            {
                "id": 1,
                "model_label": "pest_1",
                # zh_scientific_name is missing
                "latin_name": "Pestus oneus",
                "category": "Pest",
                "action_policy": "PASS"
            }
        ]
    }

    with patch("pathlib.Path.exists", return_value=True), \
         patch("builtins.open", mock_open()), \
         patch("json.load", return_value=bad_data):

        with pytest.raises(TaxonomyValidationError) as exc:
            TaxonomyService()

        msg = str(exc.value)
        assert "Field required" in msg
        assert "zh_scientific_name" in msg
