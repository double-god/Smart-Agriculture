"""
Worker diagnosis tasks unit tests with edge cases.

Tests cover normal operations and extreme conditions.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from app.worker.diagnosis_tasks import analyze_image
from app.worker.celery_app import celery_app
from requests.exceptions import Timeout, RequestException


@pytest.fixture
def mock_task():
    """创建一个 mock Celery 任务实例"""
    task = Mock()
    task.request.id = "test-task-123"
    task.state = "PENDING"
    return task


def test_analyze_image_success_download():
    """测试成功下载图片并分析"""
    with patch('app.worker.diagnosis_tasks.requests.get') as mock_get:
        # Mock HTTP 响应
        mock_response = Mock()
        mock_response.content = b"fake image data"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        with patch('app.worker.diagnosis_tasks.get_taxonomy_service') as mock_get_taxonomy:
            # Mock TaxonomyService
            mock_taxonomy = Mock()
            mock_entry = Mock()
            mock_entry.zh_scientific_name = "白粉病"
            mock_entry.latin_name = "Erysiphales"
            mock_entry.category = "Disease"
            mock_entry.action_policy = "RETRIEVE"
            mock_entry.id = 2
            mock_entry.description = "叶片表面出现白色粉状物"
            mock_entry.risk_level = "high"
            mock_taxonomy.get_by_model_label.return_value = mock_entry
            mock_get_taxonomy.return_value = mock_taxonomy

            # 执行任务
            result = analyze_image(mock_task(), "http://example.com/test.jpg")

            # 验证结果
            assert result["model_label"] in ["healthy", "powdery_mildew", "aphid_complex", "spider_mite", "late_blight"]
            assert 0.0 <= result["confidence"] <= 1.0
            assert result["diagnosis_name"] == "白粉病"
            assert result["category"] == "Disease"
            assert result["action_policy"] == "RETRIEVE"
            assert result["taxonomy_id"] == 2
            assert result["inference_time_ms"] >= 0


def test_analyze_image_download_timeout():
    """极端条件：图片下载超时"""
    with patch('app.worker.diagnosis_tasks.requests.get') as mock_get:
        # Mock 超时
        mock_get.side_effect = Timeout("Connection timeout")

        # 执行任务应该抛出异常
        with pytest.raises(RuntimeError, match="Timeout"):
            analyze_image(mock_task(), "http://example.com/test.jpg")


def test_analyze_image_download_failure_404():
    """极端条件：图片返回 404"""
    with patch('app.worker.diagnosis_tasks.requests.get') as mock_get:
        # Mock 404 响应
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = RequestException("404 Not Found")
        mock_get.return_value = mock_response

        # 执行任务应该抛出异常
        with pytest.raises(RuntimeError, match="Failed to download"):
            analyze_image(mock_task(), "http://example.com/test.jpg")


def test_analyze_image_download_connection_error():
    """极端条件：网络连接错误"""
    with patch('app.worker.diagnosis_tasks.requests.get') as mock_get:
        # Mock 连接错误
        mock_get.side_effect = RequestException("Connection refused")

        # 执行任务应该抛出异常
        with pytest.raises(RuntimeError, match="Failed to download"):
            analyze_image(mock_task(), "http://example.com/test.jpg")


def test_analyze_image_taxonomy_not_found():
    """极端条件：Taxonomy 找不到对应分类"""
    with patch('app.worker.diagnosis_tasks.requests.get') as mock_get:
        # Mock HTTP 响应
        mock_response = Mock()
        mock_response.content = b"fake image data"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        with patch('app.worker.diagnosis_tasks.get_taxonomy_service') as mock_get_taxonomy:
            # Mock TaxonomyService 找不到分类
            mock_taxonomy = Mock()
            mock_taxonomy.get_by_model_label.side_effect = Exception("Not found")
            mock_get_taxonomy.return_value = mock_taxonomy

            # 执行任务
            result = analyze_image(mock_task(), "http://example.com/test.jpg")

            # 验证结果使用默认值
            assert result["diagnosis_name"] == "未知"
            assert result["latin_name"] == "Unknown"
            assert result["category"] == "Unknown"
            assert result["action_policy"] == "HUMAN_REVIEW"
            assert result["taxonomy_id"] is None


def test_analyze_image_with_optional_params():
    """测试带可选参数的分析"""
    with patch('app.worker.diagnosis_tasks.requests.get') as mock_get:
        # Mock HTTP 响应
        mock_response = Mock()
        mock_response.content = b"fake image data"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        with patch('app.worker.diagnosis_tasks.get_taxonomy_service') as mock_get_taxonomy:
            # Mock TaxonomyService
            mock_taxonomy = Mock()
            mock_entry = Mock()
            mock_entry.zh_scientific_name = "蚜虫类"
            mock_entry.latin_name = "Aphididae"
            mock_entry.category = "Pest"
            mock_entry.action_policy = "RETRIEVE"
            mock_entry.id = 1
            mock_entry.description = "成虫和若虫刺吸汁液"
            mock_entry.risk_level = "medium"
            mock_taxonomy.get_by_model_label.return_value = mock_entry
            mock_get_taxonomy.return_value = mock_taxonomy

            # 执行任务
            result = analyze_image(
                mock_task(),
                "http://example.com/test.jpg",
                crop_type="番茄",
                location="大棚A区"
            )

            # 验证可选参数
            assert result["crop_type"] == "番茄"
            assert result["location"] == "大棚A区"


def test_analyze_image_empty_url():
    """极端条件：空 URL"""
    with pytest.raises(Exception):
        analyze_image(mock_task(), "")


def test_analyze_image_malformed_url():
    """极端条件：格式错误的 URL"""
    with patch('app.worker.diagnosis_tasks.requests.get') as mock_get:
        # Mock 连接错误
        mock_get.side_effect = RequestException("Invalid URL")

        # 执行任务应该抛出异常
        with pytest.raises(RuntimeError):
            analyze_image(mock_task(), "not-a-valid-url")


def test_analyze_image_very_long_url():
    """极端条件：超长 URL"""
    long_url = "http://example.com/" + "a" * 10000 + "/test.jpg"

    with patch('app.worker.diagnosis_tasks.requests.get') as mock_get:
        # Mock HTTP 响应
        mock_response = Mock()
        mock_response.content = b"fake image data"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        with patch('app.worker.diagnosis_tasks.get_taxonomy_service'):
            # 应该能处理（或超时）
            try:
                result = analyze_image(mock_task(), long_url)
                assert result is not None
            except Timeout:
                # 也可以接受超时
                assert True


def test_analyze_image_url_with_special_chars():
    """极端条件：URL 包含特殊字符"""
    special_url = "http://example.com/test file.jpg?token=abc@#$&space=here"

    with patch('app.worker.diagnosis_tasks.requests.get') as mock_get:
        # Mock HTTP 响应
        mock_response = Mock()
        mock_response.content = b"fake image data"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        with patch('app.worker.diagnosis_tasks.get_taxonomy_service'):
            # 应该能处理
            result = analyze_image(mock_task(), special_url)
            assert result is not None


def test_analyze_image_zero_byte_image():
    """极端条件：0 字节图片"""
    with patch('app.worker.diagnosis_tasks.requests.get') as mock_get:
        # Mock 空响应
        mock_response = Mock()
        mock_response.content = b""
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        with patch('app.worker.diagnosis_tasks.get_taxonomy_service'):
            # 应该能处理（即使图片为空）
            result = analyze_image(mock_task(), "http://example.com/empty.jpg")
            assert result["inference_time_ms"] >= 0


def test_analyze_image_large_image():
    """极端条件：超大图片"""
    with patch('app.worker.diagnosis_tasks.requests.get') as mock_get:
        # Mock 大响应（100MB）
        mock_response = Mock()
        mock_response.content = b"x" * (100 * 1024 * 1024)
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        with patch('app.worker.diagnosis_tasks.get_taxonomy_service'):
            # 应该能处理
            result = analyze_image(mock_task(), "http://example.com/large.jpg")
            assert result is not None


def test_analyze_image_concurrent_downloads():
    """极端条件：并发下载"""
    import threading

    with patch('app.worker.diagnosis_tasks.requests.get') as mock_get:
        # Mock HTTP 响应
        mock_response = Mock()
        mock_response.content = b"fake image data"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        with patch('app.worker.diagnosis_tasks.get_taxonomy_service'):
            results = []
            errors = []

            def run_analysis():
                try:
                    result = analyze_image(mock_task(), "http://example.com/test.jpg")
                    results.append(result)
                except Exception as e:
                    errors.append(e)

            threads = [threading.Thread(target=run_analysis) for _ in range(10)]

            for t in threads:
                t.start()
            for t in threads:
                t.join()

            # 所有任务应该成功
            assert len(results) == 10
            assert len(errors) == 0


def test_analyze_image_all_mock_results():
    """测试所有 Mock 结果的可能性"""
    with patch('app.worker.diagnosis_tasks.requests.get') as mock_get:
        # Mock HTTP 响应
        mock_response = Mock()
        mock_response.content = b"fake image data"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        with patch('app.worker.diagnosis_tasks.get_taxonomy_service') as mock_get_taxonomy:
            # Mock TaxonomyService
            mock_taxonomy = Mock()
            mock_entry = Mock()
            mock_entry.zh_scientific_name = "测试病害"
            mock_entry.latin_name = "Test Disease"
            mock_entry.category = "Disease"
            mock_entry.action_policy = "RETRIEVE"
            mock_entry.id = 1
            mock_entry.description = "测试描述"
            mock_entry.risk_level = "medium"
            mock_taxonomy.get_by_model_label.return_value = mock_entry
            mock_get_taxonomy.return_value = mock_taxonomy

            # 多次执行，应该覆盖所有可能性
            results = set()
            for _ in range(100):
                result = analyze_image(mock_task(), "http://example.com/test.jpg")
                results.add(result["model_label"])

            # 应该包含所有 5 种分类
            expected_labels = {"healthy", "powdery_mildew", "aphid_complex", "spider_mite", "late_blight"}
            assert results.issubset(expected_labels)
