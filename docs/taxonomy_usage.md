# TaxonomyService Usage Guide

This guide shows how to use the `TaxonomyService` in the Smart-Agriculture system.

## Table of Contents

- [Basic Usage](#basic-usage)
- [FastAPI Integration](#fastapi-integration)
- [RAG Keyword Retrieval](#rag-keyword-retrieval)
- [Error Handling](#error-handling)
- [Complete Examples](#complete-examples)

---

## Basic Usage

### Getting the Service Instance

The `TaxonomyService` is a singleton, so you can get the instance using the factory function:

```python
from app.services.taxonomy_service import get_taxonomy_service

# Get the singleton instance
taxonomy = get_taxonomy_service()

# Access metadata
print(f"Taxonomy version: {taxonomy.metadata.version}")
print(f"Last updated: {taxonomy.metadata.last_updated}")
```

### Querying by ID

```python
from app.services.taxonomy_service import get_taxonomy_service

taxonomy = get_taxonomy_service()

# Get entry by ID
entry = taxonomy.get_by_id(3)

print(f"ID: {entry.id}")
print(f"Name: {entry.zh_scientific_name}")
print(f"Latin Name: {entry.latin_name}")
print(f"Category: {entry.category}")
print(f"Action Policy: {entry.action_policy}")
# Output:
# ID: 3
# Name: 叶螨
# Latin Name: Tetranychus urticae
# Category: Pest
# Action Policy: RETRIEVE
```

### Querying by Model Label

```python
from app.services.taxonomy_service import get_taxonomy_service

taxonomy = get_taxonomy_service()

# Get entry by CV model output label
entry = taxonomy.get_by_model_label("aphid_complex")

print(f"Chinese name: {entry.zh_scientific_name}")
print(f"Description: {entry.description}")
# Output:
# Chinese name: 蚜虫类
# Description: 包括棉蚜、桃蚜等常见蚜虫
```

### Querying by Chinese Name

```python
from app.services.taxonomy_service import get_taxonomy_service

taxonomy = get_taxonomy_service()

# Get entry by Chinese scientific name
entry = taxonomy.get_by_name("白粉病")

print(f"Model label: {entry.model_label}")
print(f"Risk level: {entry.risk_level}")
# Output:
# Model label: powdery_mildew
# Risk level: High
```

---

## FastAPI Integration

### Using Dependency Injection

The recommended way to use `TaxonomyService` in FastAPI routes is through dependency injection:

```python
from fastapi import APIRouter, Depends, HTTPException
from app.core.deps import depends_taxonomy
from app.services.taxonomy_service import TaxonomyService, TaxonomyNotFoundError

router = APIRouter()

@router.get("/diagnosis/{taxonomy_id}")
async def get_diagnosis_info(
    taxonomy_id: int,
    taxonomy: TaxonomyService = Depends(depends_taxonomy)
):
    """
    Get diagnosis information by taxonomy ID.

    Args:
        taxonomy_id: The taxonomy entry ID
        taxonomy: Injected TaxonomyService instance

    Returns:
        Diagnosis information with Chinese name and action policy
    """
    try:
        entry = taxonomy.get_by_id(taxonomy_id)
        return {
            "id": entry.id,
            "name": entry.zh_scientific_name,
            "latin_name": entry.latin_name,
            "category": entry.category,
            "action_policy": entry.action_policy,
            "risk_level": entry.risk_level
        }
    except TaxonomyNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
```

### Processing CV Model Results

```python
from fastapi import APIRouter, Depends
from app.core.deps import depends_taxonomy
from pydantic import BaseModel

class CVModelResult(BaseModel):
    class_id: int
    confidence: float

@router.post("/diagnosis/interpret")
async def interpret_cv_result(
    result: CVModelResult,
    taxonomy: TaxonomyService = Depends(depends_taxonomy)
):
    """
    Interpret CV model result using taxonomy.

    Maps class_id to taxonomy entry and provides action policy.
    """
    entry = taxonomy.get_by_id(result.class_id)

    return {
        "detected_disease": entry.zh_scientific_name,
        "category": entry.category,
        "confidence": result.confidence,
        "recommended_action": entry.action_policy,
        "risk_level": entry.risk_level
    }
```

---

## RAG Keyword Retrieval

### Getting Search Keywords

The `get_search_keywords()` method returns keywords for ChromaDB retrieval:

```python
from app.services.taxonomy_service import get_taxonomy_service

taxonomy = get_taxonomy_service()

# Get search keywords for RAG
keywords = taxonomy.get_search_keywords(3)

print(f"Keywords: {keywords}")
# Output: Keywords: ['红蜘蛛', '二斑叶螨']

# Use in ChromaDB query
# query_results = collection.query(query_texts=keywords, n_results=5)
```

### Building RAG Queries

```python
from app.services.taxonomy_service import get_taxonomy_service

taxonomy = get_taxonomy_service()

def get_rag_context(taxonomy_id: int) -> dict:
    """
    Get RAG context for a taxonomy entry.

    Returns search keywords and metadata for vector database queries.
    """
    entry = taxonomy.get_by_id(taxonomy_id)
    keywords = taxonomy.get_search_keywords(taxonomy_id)

    return {
        "taxonomy_id": taxonomy_id,
        "disease_name": entry.zh_scientific_name,
        "search_keywords": keywords,
        "category": entry.category,
        "action_policy": entry.action_policy
    }

# Usage
context = get_rag_context(2)
print(context)
# {
#     "taxonomy_id": 2,
#     "disease_name": "白粉病",
#     "search_keywords": ["白粉病", "真菌性病害"],
#     "category": "Disease",
#     "action_policy": "RETRIEVE"
# }
```

---

## Error Handling

### Handling Missing Entries

The service raises `TaxonomyNotFoundError` for invalid queries:

```python
from app.services.taxonomy_service import (
    get_taxonomy_service,
    TaxonomyNotFoundError
)

taxonomy = get_taxonomy_service()

try:
    entry = taxonomy.get_by_id(999)
except TaxonomyNotFoundError as e:
    print(f"Error: {e}")
    # Output: Error: Taxonomy ID 999 not found

    # Handle the error
    print("Please provide a valid taxonomy ID (0-4)")
```

### Validation in Routes

```python
from fastapi import Depends, HTTPException
from app.services.taxonomy_service import TaxonomyNotFoundError

async def safe_taxonomy_lookup(
    taxonomy_id: int,
    taxonomy: TaxonomyService = Depends(depends_taxonomy)
):
    """Safe taxonomy lookup with error handling."""
    try:
        return taxonomy.get_by_id(taxonomy_id)
    except TaxonomyNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Taxonomy entry {taxonomy_id} not found. Valid IDs: 0-4"
        )
```

---

## Complete Examples

### Example 1: CV Model to Diagnosis

```python
from app.services.taxonomy_service import get_taxonomy_service

def process_diagnosis(class_id: int, confidence: float) -> dict:
    """
    Process CV model output into a diagnosis result.

    Args:
        class_id: CV model class output
        confidence: Model confidence score

    Returns:
        Diagnosis result with action policy
    """
    taxonomy = get_taxonomy_service()

    try:
        entry = taxonomy.get_by_id(class_id)

        return {
            "status": "success",
            "disease": entry.zh_scientific_name,
            "latin_name": entry.latin_name,
            "category": entry.category,
            "confidence": confidence,
            "action_policy": entry.action_policy,
            "risk_level": entry.risk_level,
            "note": entry.note
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

# Usage
result = process_diagnosis(3, 0.95)
print(result)
# {
#     "status": "success",
#     "disease": "叶螨",
#     "latin_name": "Tetranychus urticae",
#     "category": "Pest",
#     "confidence": 0.95,
#     "action_policy": "RETRIEVE",
#     "risk_level": "High",
#     "note": None
# }
```

### Example 2: Batch Processing

```python
from app.services.taxonomy_service import get_taxonomy_service

def batch_get_entries(ids: list[int]) -> list[dict]:
    """
    Get multiple taxonomy entries by IDs.

    Args:
        ids: List of taxonomy IDs

    Returns:
        List of entry dictionaries
    """
    taxonomy = get_taxonomy_service()
    results = []

    for tid in ids:
        try:
            entry = taxonomy.get_by_id(tid)
            results.append({
                "id": entry.id,
                "name": entry.zh_scientific_name,
                "category": entry.category
            })
        except Exception as e:
            results.append({
                "id": tid,
                "error": str(e)
            })

    return results

# Usage
entries = batch_get_entries([0, 1, 2, 3, 4, 999])
print(entries)
```

### Example 3: RAG Integration

```python
from app.services.taxonomy_service import get_taxonomy_service

def build_rag_query(taxonomy_id: int) -> dict:
    """
    Build RAG query for vector database search.

    Args:
        taxonomy_id: Taxonomy entry ID

    Returns:
        Query configuration for ChromaDB
    """
    taxonomy = get_taxonomy_service()
    entry = taxonomy.get_by_id(taxonomy_id)
    keywords = taxonomy.get_search_keywords(taxonomy_id)

    return {
        "query_texts": keywords,
        "n_results": 5,
        "where": {
            "category": entry.category
        }
    }

# Usage
query = build_rag_query(3)
# query = {
#     "query_texts": ["红蜘蛛", "二斑叶螨"],
#     "n_results": 5,
#     "where": {"category": "Pest"}
# }
```

---

## Tips and Best Practices

1. **Always use dependency injection in FastAPI routes** - This makes testing easier and ensures proper singleton behavior.

2. **Handle `TaxonomyNotFoundError` gracefully** - Provide helpful error messages to users when an invalid ID is provided.

3. **Cache RAG keywords** - Search keywords are static, so cache them if you're doing many lookups.

4. **Use type hints** - The service is fully typed, so leverage IDE autocomplete.

5. **Check action_policy** - Always check the `action_policy` field before deciding on next steps (PASS, RETRIEVE, or HUMAN_REVIEW).

---

## See Also

- [TaxonomyService API Documentation](../app/services/taxonomy_service.py)
- [Taxonomy Data Models](../app/models/taxonomy.py)
- [OpenSpec: Taxonomy Specification](../openspec/changes/implement-taxonomy-service/specs/taxonomy/spec.md)
