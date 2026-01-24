"""
Smoke tests for diagnosis workflow - basic functionality tests.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from app.api.main import app

client = TestClient(app)


def test_create_diagnosis_task_smoke():
    """冒烟测试：创建诊断任务"""
    with patch('app.worker.diagnosis_tasks.analyze_image') as mock_analyze:
        # Mock Celery task
        mock_task = Mock()
        mock_task.id = "test-task-123"
        mock_task.state = "PENDING"
        mock_analyze.delay.return_value = mock_task

        request_data = {
            "image_url": "http://localhost:9010/smart-agriculture/test.jpg"
        }

        response = client.post("/api/v1/diagnose", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert data["task_id"] == "test-task-123"
        assert data["status"] == "PENDING"


def test_get_task_status_smoke():
    """冒烟测试：查询任务状态"""
    with patch('celery.result.AsyncResult') as mock_result:
        # Mock AsyncResult
        mock_result_instance = Mock()
        mock_result_instance.state = "PENDING"
        mock_result_instance.result = None
        mock_result.return_value = mock_result_instance

        response = client.get("/api/v1/diagnose/tasks/test-task-123")

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "test-task-123"
        assert data["status"] == "PENDING"


def test_upload_image_smoke():
    """冒烟测试：上传图片"""
    with patch('app.api.endpoints.upload.StorageService') as mock_storage_class:
        # Mock StorageService
        mock_storage = Mock()
        mock_storage.upload_image.return_value = "http://localhost:9010/smart-agriculture/uuid_test.jpg"
        mock_storage_class.return_value = mock_storage

        from io import BytesIO
        image_content = b"fake image data"
        files = {"file": ("test.jpg", BytesIO(image_content), "image/jpeg")}

        response = client.post("/api/v1/upload", files=files)

        assert response.status_code == 200
        data = response.json()
        assert "url" in data
        assert data["url"] == "http://localhost:9010/smart-agriculture/uuid_test.jpg"


def test_upload_unsupported_file_type():
    """测试上传不支持的文件类型"""
    from io import BytesIO
    files = {"file": ("test.pdf", BytesIO(b"fake pdf"), "application/pdf")}

    response = client.post("/api/v1/upload", files=files)

    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_upload_empty_file():
    """测试上传空文件"""
    from io import BytesIO
    files = {"file": ("empty.jpg", BytesIO(b""), "image/jpeg")}

    response = client.post("/api/v1/upload", files=files)

    assert response.status_code == 400
    assert "Empty file" in response.json()["detail"]


def test_upload_oversized_file():
    """测试上传超大文件（> 10MB）"""
    from io import BytesIO
    # 创建 11MB 的文件
    large_content = b"x" * (11 * 1024 * 1024)
    files = {"file": ("large.jpg", BytesIO(large_content), "image/jpeg")}

    response = client.post("/api/v1/upload", files=files)

    assert response.status_code == 400
    assert "File too large" in response.json()["detail"]


def test_invalid_image_url():
    """测试无效的 URL 格式"""
    request_data = {
        "image_url": "not-a-valid-url"
    }

    response = client.post("/api/v1/diagnose", json=request_data)

    assert response.status_code == 422


def test_missing_image_url():
    """测试缺少 image_url 字段"""
    request_data = {
        "crop_type": "番茄"
    }

    response = client.post("/api/v1/diagnose", json=request_data)

    assert response.status_code == 422
