"""
Taxonomy data models for Smart-Agriculture system.

This module defines Pydantic models that match the JSON structure of
data/taxonomy_standard_v1.json for pest and disease classification.
"""

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
    model_label: str = Field(
        ..., description="CV model output label (e.g., 'spider_mite')"
    )
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
    description: Optional[str] = Field(default=None, description="Additional description")
    risk_level: Optional[str] = Field(
        default=None, description="Risk level (e.g., 'High', 'Medium')"
    )
    note: Optional[str] = Field(default=None, description="Additional notes")


class TaxonomyStandard(BaseModel):
    """Complete taxonomy standard loaded from JSON."""

    metadata: Metadata
    taxonomy: List[TaxonomyEntry]
