"""
Taxonomy API endpoints for Smart Agriculture system.

This module provides REST API endpoints for querying taxonomy data
including pest and disease classifications.
"""

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from typing import List

from app.services.taxonomy_service import (
    TaxonomyService,
    TaxonomyNotFoundError,
    TaxonomyEntry,
)
from app.core import depends_taxonomy

router = APIRouter(prefix="/api/v1/taxonomy", tags=["taxonomy"])


@router.get("/search")
async def search_taxonomy(
    q: str = Query(..., min_length=1, max_length=100, description="搜索关键词（中文名称或模型标签）"),
    taxonomy: TaxonomyService = Depends(depends_taxonomy),
) -> List[TaxonomyEntry]:
    """
    根据中文名称或模型标签搜索分类条目。

    Args:
        q: 搜索关键词，支持中文名称或模型标签
        taxonomy: TaxonomyService 依赖注入

    Returns:
        List[TaxonomyEntry]: 匹配的分类条目列表

    Raises:
        HTTPException: 当未找到匹配结果时返回 404

    Example:
        GET /api/v1/taxonomy/search?q=白粉病
        Response:
        [
            {
                "id": 2,
                "model_label": "powdery_mildew",
                "zh_scientific_name": "白粉病",
                "latin_name": "Erysiphales",
                "category": "Disease",
                "action_policy": "RETRIEVE",
                "search_keywords": ["白粉", "粉病"],
                "description": "叶片表面出现白色粉状物...",
                "risk_level": "high",
                "note": null
            }
        ]
    """
    results = []

    # 尝试按中文名称搜索
    try:
        result = taxonomy.get_by_name(q)
        results.append(result)
    except TaxonomyNotFoundError:
        pass

    # 尝试按模型标签搜索
    try:
        result = taxonomy.get_by_model_label(q)
        # 避免重复（如果同一条目同时匹配名称和标签）
        if result not in results:
            results.append(result)
    except TaxonomyNotFoundError:
        pass

    if not results:
        raise HTTPException(
            status_code=404,
            detail=f"Taxonomy entry not found for query: '{q}'"
        )

    return results


@router.get("/{id}")
async def get_taxonomy_entry(
    id: int = Path(..., ge=0, le=1000, description="分类 ID (0-1000)"),
    taxonomy: TaxonomyService = Depends(depends_taxonomy),
) -> TaxonomyEntry:
    """
    根据 ID 查询分类条目。

    Args:
        id: 分类唯一标识符
        taxonomy: TaxonomyService 依赖注入

    Returns:
        TaxonomyEntry: 分类条目对象

    Raises:
        HTTPException: 当 ID 不存在时返回 404

    Example:
        GET /api/v1/taxonomy/1
        Response:
        {
            "id": 1,
            "model_label": "aphid_complex",
            "zh_scientific_name": "蚜虫类",
            "latin_name": "Aphididae",
            "category": "Pest",
            "action_policy": "RETRIEVE",
            "search_keywords": ["蚜虫", "腻虫"],
            "description": "成虫和若虫刺吸汁液...",
            "risk_level": "medium",
            "note": null
        }
    """
    try:
        return taxonomy.get_by_id(id)
    except TaxonomyNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
