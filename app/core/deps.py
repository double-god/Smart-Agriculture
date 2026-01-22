"""
FastAPI dependency injection utilities for Smart-Agriculture system.

This module provides dependency injection functions for FastAPI routes.
"""

from typing import TYPE_CHECKING
from fastapi import Depends

if TYPE_CHECKING:
    from app.services.taxonomy_service import TaxonomyService
    from app.services.storage import StorageService

# Lazy imports to avoid circular dependency
def _get_taxonomy_service():
    from app.services.taxonomy_service import get_taxonomy_service
    return get_taxonomy_service


def _get_storage_service():
    from app.services.storage import get_storage_service
    return get_storage_service


async def depends_taxonomy(
    service: "TaxonomyService" = Depends(_get_taxonomy_service),
) -> "TaxonomyService":
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

    Returns:
        TaxonomyService: The singleton taxonomy service instance
    """
    return service


async def depends_storage(
    service: "StorageService" = Depends(_get_storage_service),
) -> "StorageService":
    """
    FastAPI dependency injection for StorageService.

    Usage in routes:
        @app.post("/upload")
        async def upload_diagnosis_image(
            file: UploadFile,
            storage: StorageService = Depends(depends_storage)
        ):
            url = storage.upload_image(file.file, file.filename)
            return {"url": url}

    Returns:
        StorageService: The singleton storage service instance
    """
    return service
