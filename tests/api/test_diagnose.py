"""
Diagnosis API integration tests with edge cases.

Tests cover normal operations and extreme conditions.
"""

import pytest
from fastapi.testclient import TestClient
from app.api.main import app

client = TestClient(app)


def test_create_diagnosis_task_success():
    """测试成功创建诊断任务"""
    request_data = {
        "image_url": "http://localhost:9010/smart-agriculture/test.jpg",
        "crop_type": "番茄"
    }

    response = client.post("/api/v1/diagnose", json=request_data)

    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data
    assert "status" in data
    assert data["status"] in ["PENDING", "STARTED"]
    assert data["message"] == "Diagnosis task created successfully"


def test_create_diagnosis_task_minimal():
    """测试最小参数创建诊断任务"""
    request_data = {
        "image_url": "http://localhost:9010/smart-agriculture/test.jpg"
    }

    response = client.post("/api/v1/diagnose", json=request_data)

    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data


def test_create_diagnosis_task_full_params():
    """测试完整参数创建诊断任务"""
    request_data = {
        "image_url": "http://localhost:9010/smart-agriculture/test.jpg",
        "crop_type": "黄瓜",
        "location": "大棚B区"
    }

    response = client.post("/api/v1/diagnose", json=request_data)

    assert response.status_code == 200


def test_invalid_image_url_format():
    """极端条件：无效的 URL 格式"""
    request_data = {
        "image_url": "not-a-valid-url",
        "crop_type": "番茄"
    }

    response = client.post("/api/v1/diagnose", json=request_data)

    # Pydantic 验证应该拒绝
    assert response.status_code == 422


def test_empty_image_url():
    """极端条件：空的图片 URL"""
    request_data = {
        "image_url": ""
    }

    response = client.post("/api/v1/diagnose", json=request_data)

    assert response.status_code == 422


def test_missing_image_url():
    """极端条件：缺少 image_url 字段"""
    request_data = {
        "crop_type": "番茄"
    }

    response = client.post("/api/v1/diagnose", json=request_data)

    assert response.status_code == 422


def test_very_long_crop_type():
    """极端条件：超长的 crop_type"""
    request_data = {
        "image_url": "http://localhost:9010/smart-agriculture/test.jpg",
        "crop_type": "A" * 10000
    }

    response = client.post("/api/v1/diagnose", json=request_data)

    # 应该接受或拒绝，取决于验证规则
    assert response.status_code in [200, 422]


def test_special_characters_in_location():
    """极端条件：location 包含特殊字符"""
    request_data = {
        "image_url": "http://localhost:9010/smart-agriculture/test.jpg",
        "location": "大棚A区@#$%^&*()"
    }

    response = client.post("/api/v1/diagnose", json=request_data)

    assert response.status_code == 200


def test_unicode_in_crop_type():
    """极端条件：crop_type 包含 Unicode 字符"""
    request_data = {
        "image_url": "http://localhost:9010/smart-agriculture/test.jpg",
        "crop_type": "番茄🍅"
    }

    response = client.post("/api/v1/diagnose", json=request_data)

    assert response.status_code == 200


def test_get_task_status_success():
    """测试查询任务状态"""
    # 先创建任务
    create_response = client.post("/api/v1/diagnose", json={
        "image_url": "http://localhost:9010/smart-agriculture/test.jpg"
    })
    task_id = create_response.json()["task_id"]

    # 查询状态
    response = client.get(f"/api/v1/diagnose/tasks/{task_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == task_id
    assert data["status"] in ["PENDING", "STARTED", "SUCCESS"]


def test_get_task_status_not_found():
    """极端条件：查询不存在的任务 ID"""
    fake_task_id = "00000000-0000-0000-0000-000000000000"
    response = client.get(f"/api/v1/diagnose/tasks/{fake_task_id}")

    # 应该返回 PENDING 状态（Celery 默认行为）
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "PENDING"


def test_get_task_status_invalid_id():
    """极端条件：无效的任务 ID 格式"""
    response = client.get("/api/v1/diagnose/tasks/invalid-uuid")

    # 可能返回 400 或 422
    assert response.status_code in [200, 400, 422]


def test_get_task_status_empty_id():
    """极端条件：空的任务 ID"""
    response = client.get("/api/v1/diagnose/tasks/")

    assert response.status_code == 404  # Not Found


def test_create_task_concurrent():
    """极端条件：并发创建任务"""
    import threading
    import time

    results = []
    task_ids = []

    def create_task():
        request_data = {
            "image_url": "http://localhost:9010/smart-agriculture/test.jpg"
        }
        response = client.post("/api/v1/diagnose", json=request_data)
        results.append(response.status_code)
        if response.status_code == 200:
            task_ids.append(response.json()["task_id"])

    threads = [threading.Thread(target=create_task) for _ in range(20)]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # 所有请求应该成功
    assert all(status == 200 for status in results)
    # 所有任务 ID 应该不同
    assert len(task_ids) == len(set(task_ids))


def test_very_long_image_url():
    """极端条件：超长的图片 URL"""
    long_url = "http://localhost:9010/smart-agriculture/" + "a" * 10000 + ".jpg"
    request_data = {
        "image_url": long_url
    }

    response = client.post("/api/v1/diagnose", json=request_data)

    # 应该接受或拒绝
    assert response.status_code in [200, 422]


def test_image_url_with_fragment():
    """极端条件：URL 包含 fragment"""
    request_data = {
        "image_url": "http://localhost:9010/smart-agriculture/test.jpg#fragment"
    }

    response = client.post("/api/v1/diagnose", json=request_data)

    assert response.status_code == 200


def test_image_url_with_query_params():
    """极端条件：URL 包含查询参数"""
    request_data = {
        "image_url": "http://localhost:9010/smart-agriculture/test.jpg?token=abc123&expires=1234567890"
    }

    response = client.post("/api/v1/diagnose", json=request_data)

    assert response.status_code == 200


def test_null_optional_fields():
    """边界条件：可选字段显式设为 null"""
    request_data = {
        "image_url": "http://localhost:9010/smart-agriculture/test.jpg",
        "crop_type": None,
        "location": None
    }

    response = client.post("/api/v1/diagnose", json=request_data)

    assert response.status_code == 200


def test_extra_fields():
    """极端条件：包含额外字段"""
    request_data = {
        "image_url": "http://localhost:9010/smart-agriculture/test.jpg",
        "crop_type": "番茄",
        "extra_field": "should be ignored",
        "another_field": 12345
    }

    response = client.post("/api/v1/diagnose", json=request_data)

    # FastAPI 应该忽略额外字段
    assert response.status_code == 200


def test_malformed_json():
    """极端条件：格式错误的 JSON"""
    response = client.post(
        "/api/v1/diagnose",
        data="{invalid json}",
        headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 422


def test_empty_json_body():
    """极端条件：空的 JSON 请求体"""
    response = client.post(
        "/api/v1/diagnose",
        json={},
        headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 422


def test_wrong_content_type():
    """极端条件：错误的 Content-Type"""
    response = client.post(
        "/api/v1/diagnose",
        data='{"image_url": "http://localhost:9010/smart-agriculture/test.jpg"}',
        headers={"Content-Type": "text/plain"}
    )

    # FastAPI 可能会拒绝或尝试解析
    assert response.status_code in [415, 422, 200]


def test_sql_injection_in_crop_type():
    """极端条件：SQL 注入尝试"""
    request_data = {
        "image_url": "http://localhost:9010/smart-agriculture/test.jpg",
        "crop_type": "'); DROP TABLE crops; --"
    }

    response = client.post("/api/v1/diagnose", json=request_data)

    # 应该正常处理（无 SQL 操作）
    assert response.status_code == 200


def test_xss_in_location():
    """极端条件：XSS 尝试"""
    request_data = {
        "image_url": "http://localhost:9010/smart-agriculture/test.jpg",
        "location": "<script>alert('xss')</script>"
    }

    response = client.post("/api/v1/diagnose", json=request_data)

    # 应该正常接受并转义
    assert response.status_code == 200
