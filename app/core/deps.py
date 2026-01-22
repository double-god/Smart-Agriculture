"""
FastAPI dependency injection utilities for Smart-Agriculture system.

This module provides dependency injection functions for FastAPI routes.
"""

from fastapi import Depends
from app.services.taxonomy_service import TaxonomyService, get_taxonomy_service


async def depends_taxonomy(
    service: TaxonomyService = Depends(get_taxonomy_service),
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

    Returns:
        TaxonomyService: The singleton taxonomy service instance
    """
    return service
