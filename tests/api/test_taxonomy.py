"""
Integration tests for Taxonomy API endpoints.

Tests cover all HTTP endpoints including success cases and error handling.
"""

import pytest
from fastapi.testclient import TestClient
from app.api.main import app

client = TestClient(app)


def test_get_taxonomy_by_id_success():
    """测试查询存在的 ID"""
    response = client.get("/api/v1/taxonomy/1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["zh_scientific_name"] == "蚜虫类"
    assert data["model_label"] == "aphid_complex"
    assert data["category"] == "Pest"


def test_get_taxonomy_by_id_not_found():
    """测试查询不存在的 ID"""
    response = client.get("/api/v1/taxonomy/999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_search_taxonomy_by_chinese_name():
    """测试按中文名称搜索"""
    response = client.get("/api/v1/taxonomy/search?q=白粉病")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["zh_scientific_name"] == "白粉病"
    assert data[0]["model_label"] == "powdery_mildew"


def test_search_taxonomy_by_model_label():
    """测试按模型标签搜索"""
    response = client.get("/api/v1/taxonomy/search?q=aphid_complex")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["model_label"] == "aphid_complex"
    assert data[0]["zh_scientific_name"] == "蚜虫类"


def test_search_taxonomy_not_found():
    """测试搜索不存在的关键词"""
    response = client.get("/api/v1/taxonomy/search?q=不存在的病害")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_invalid_id_parameter():
    """测试无效的 ID 参数"""
    response = client.get("/api/v1/taxonomy/abc")
    assert response.status_code == 422


def test_id_out_of_range():
    """测试 ID 超出范围"""
    response = client.get("/api/v1/taxonomy/1001")
    assert response.status_code == 422


def test_search_empty_query():
    """测试空搜索关键词"""
    response = client.get("/api/v1/taxonomy/search?q=")
    assert response.status_code == 422


def test_get_healthy_entry():
    """测试查询健康状态（ID=0）"""
    response = client.get("/api/v1/taxonomy/0")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 0
    assert data["model_label"] == "healthy"
    assert data["category"] == "Status"


def test_search_returns_single_result():
    """测试搜索返回单个结果"""
    response = client.get("/api/v1/taxonomy/search?q=spider_mite")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["model_label"] == "spider_mite"
