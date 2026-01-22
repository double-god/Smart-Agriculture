"""
Unit tests for TaxonomyService.

Tests cover loading, querying, error handling, and singleton behavior.
"""

import pytest
from app.services.taxonomy_service import (
    TaxonomyService,
    TaxonomyNotFoundError,
    get_taxonomy_service,
)


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
