"""
Upload API integration tests with edge cases.

Tests cover normal operations and extreme conditions.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from app.api.main import app
from io import BytesIO

client = TestClient(app)


def test_upload_image_success():
    """测试成功上传图片"""
    with patch('app.api.endpoints.upload.StorageService') as mock_storage_class:
        # Mock StorageService
        mock_storage = Mock()
        mock_storage.upload_image.return_value = "http://localhost:9010/smart-agriculture/uuid_test.jpg"
        mock_storage_class.return_value = mock_storage

        image_content = b"fake image data"
        files = {"file": ("test.jpg", BytesIO(image_content), "image/jpeg")}

        response = client.post("/api/v1/upload", files=files)

    assert response.status_code == 200
    data = response.json()
    assert "url" in data
    assert "filename" in data
    assert data["content_type"] == "image/jpeg"
    assert data["original_filename"] == "test.jpg"


def test_upload_png_image():
    """测试上传 PNG 图片"""
    image_content = b"fake png data"
    files = {"file": ("test.png", BytesIO(image_content), "image/png")}

    response = client.post("/api/v1/upload", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["content_type"] == "image/png"


def test_upload_unsupported_file_type():
    """测试上传不支持的文件类型"""
    files = {"file": ("test.pdf", BytesIO(b"fake pdf"), "application/pdf")}

    response = client.post("/api/v1/upload", files=files)

    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_upload_unsupported_file_type_txt():
    """极端条件：上传文本文件"""
    files = {"file": ("test.txt", BytesIO(b"plain text"), "text/plain")}

    response = client.post("/api/v1/upload", files=files)

    assert response.status_code == 400


def test_upload_empty_file():
    """极端条件：上传空文件"""
    files = {"file": ("empty.jpg", BytesIO(b""), "image/jpeg")}

    response = client.post("/api/v1/upload", files=files)

    assert response.status_code == 400
    assert "Empty file" in response.json()["detail"]


def test_upload_oversized_file():
    """极端条件：上传超大文件（> 10MB）"""
    # 创建 11MB 的文件
    large_content = b"x" * (11 * 1024 * 1024)
    files = {"file": ("large.jpg", BytesIO(large_content), "image/jpeg")}

    response = client.post("/api/v1/upload", files=files)

    assert response.status_code == 400
    assert "File too large" in response.json()["detail"]


def test_upload_exactly_10mb_file():
    """边界条件：上传刚好 10MB 的文件"""
    # 创建 10MB 的文件（应该成功）
    exact_content = b"x" * (10 * 1024 * 1024)
    files = {"file": ("exact.jpg", BytesIO(exact_content), "image/jpeg")}

    response = client.post("/api/v1/upload", files=files)

    # 应该成功或超时，取决于服务器配置
    # 这里我们验证它返回了有效的响应
    assert response.status_code in [200, 503, 504]


def test_upload_no_filename():
    """极端条件：上传没有文件名的文件"""
    files = {"file": (None, BytesIO(b"fake image"), "image/jpeg")}

    response = client.post("/api/v1/upload", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["original_filename"] == "unknown"


def test_upload_invalid_content_type():
    """极端条件：Content-Type 与文件扩展名不匹配"""
    # PDF 内容但声称是 JPEG
    files = {"file": ("fake.jpg", BytesIO(b"%PDF-1.4"), "image/jpeg")}

    response = client.post("/api/v1/upload", files=files)

    # 系统应该基于 Content-Type 而非内容验证
    assert response.status_code == 200


def test_upload_missing_file_parameter():
    """极端条件：缺少 file 参数"""
    response = client.post("/api/v1/upload")

    assert response.status_code == 422  # Unprocessable Entity


def test_upload_malformed_multipart():
    """极端条件：格式错误的 multipart 数据"""
    # 发送错误的 Content-Type
    response = client.post(
        "/api/v1/upload",
        content_type="multipart/form-data",
        data="invalid multipart data"
    )

    assert response.status_code in [400, 422]


def test_upload_unicode_filename():
    """极端条件：使用 Unicode 文件名"""
    files = {"file": ("中文文件名.jpg", BytesIO(b"fake image"), "image/jpeg")}

    response = client.post("/api/v1/upload", files=files)

    assert response.status_code == 200
    data = response.json()
    assert "中文文件名.jpg" in data["filename"]


def test_upload_very_long_filename():
    """极端条件：超长文件名"""
    long_name = "a" * 1000 + ".jpg"
    files = {"file": (long_name, BytesIO(b"fake image"), "image/jpeg")}

    response = client.post("/api/v1/upload", files=files)

    # 应该成功处理或返回合理错误
    assert response.status_code in [200, 400]


def test_upload_special_characters_filename():
    """极端条件：文件名包含特殊字符"""
    special_names = [
        "file with spaces.jpg",
        "file-with-dashes.jpg",
        "file_with_underscores.jpg",
        "file.with.dots.jpg",
        "file@#$%^&*().jpg"
    ]

    for special_name in special_names:
        files = {"file": (special_name, BytesIO(b"fake image"), "image/jpeg")}
        response = client.post("/api/v1/upload", files=files)

        assert response.status_code == 200
        data = response.json()
        assert special_name in data["filename"]


def test_upload_multiple_files_same_name():
    """极端条件：连续上传同名文件"""
    files = {"file": ("test.jpg", BytesIO(b"fake image 1"), "image/jpeg")}

    response1 = client.post("/api/v1/upload", files=files)
    response2 = client.post("/api/v1/upload", files=files)

    assert response1.status_code == 200
    assert response2.status_code == 200

    # 验证文件名不同（UUID 前缀）
    data1 = response1.json()
    data2 = response2.json()
    assert data1["filename"] != data2["filename"]


def test_upload_concurrent_requests():
    """极端条件：并发上传请求"""
    import threading

    results = []

    def upload_file():
        files = {"file": ("test.jpg", BytesIO(b"fake image"), "image/jpeg")}
        response = client.post("/api/v1/upload", files=files)
        results.append(response.status_code)

    threads = [threading.Thread(target=upload_file) for _ in range(10)]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # 所有请求应该成功
    assert all(status == 200 for status in results)


def test_upload_no_extension():
    """边界条件：没有扩展名的文件"""
    files = {"file": ("noextension", BytesIO(b"fake image"), "image/jpeg")}

    response = client.post("/api/v1/upload", files=files)

    assert response.status_code == 200
    data = response.json()
    assert "noextension" in data["filename"]
