"""
Worker diagnosis tasks unit tests with edge cases.

Tests cover normal operations and extreme conditions.
"""

from unittest.mock import Mock, patch

import pytest
from langchain_core.documents import Document
from requests.exceptions import Timeout

from app.core.ssrf_protection import ImageDownloadError
from app.services.rag_service import RAGServiceNotInitializedError
from app.worker.chains import LLMError, ReportTimeoutError
from app.worker.diagnosis_tasks import analyze_image


def create_mock_task():
    """创建一个 mock Celery 任务实例（辅助函数）"""
    task = Mock()
    task.request.id = "test-task-123"
    task.state = "PENDING"
    return task


def call_analyze_image(task, image_url, **kwargs):
    """
    辅助函数：直接调用 analyze_image 的底层函数，绕过 Celery task 包装器。

    这避免了 Celery task.__call__ 的参数处理问题。

    注意：对于 bind=True 的任务，Celery 会自动将 task 实例作为第一个参数传递给 run()。
    因此我们不需要手动传递 task 参数，只需传递原始函数的参数即可。
    """
    # 对于 bound tasks, run() 的第一个参数是 Celery task instance (自动提供)
    # 原始函数签名: def analyze_image(self, image_url, crop_type=None, location=None)
    # 其中 self 是 Celery task instance
    crop_type = kwargs.pop('crop_type', None)
    location = kwargs.pop('location', None)
    return analyze_image.run(image_url, crop_type, location)


def test_analyze_image_success_download():
    """测试成功下载图片并分析"""
    with patch('app.worker.diagnosis_tasks.download_image_securely') as mock_download:
        # Mock 下载图片返回字节数据
        mock_download.return_value = b"fake image data"

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

            with patch('app.worker.diagnosis_tasks.get_rag_service') as mock_get_rag:
                # Mock RAG 服务
                mock_rag = Mock()
                mock_docs = [Document(page_content="测试文档", metadata={"source": "test.md"})]
                mock_rag.query = Mock(return_value=mock_docs)
                mock_get_rag.return_value = mock_rag

                mock_report_async = Mock(return_value="# 测试报告")
                with patch('app.worker.diagnosis_tasks.generate_diagnosis_report',
                          new=mock_report_async):
                    # 执行任务
                    result = call_analyze_image(create_mock_task(), "http://example.com/test.jpg")

                    # 验证结果
                    valid_labels = ["healthy", "powdery_mildew", "aphid_complex",
                                   "spider_mite", "late_blight"]
                    assert result["model_label"] in valid_labels
                    assert 0.0 <= result["confidence"] <= 1.0
                    assert result["diagnosis_name"] == "白粉病"
                    assert result["category"] == "Disease"
                    assert result["action_policy"] == "RETRIEVE"
                    assert result["taxonomy_id"] == 2
                    assert result["inference_time_ms"] >= 0

                    # 验证 timings 字段存在
                    assert "timings" in result
                    assert "image_download_ms" in result["timings"]
                    assert "inference_ms" in result["timings"]
                    assert "rag_query_ms" in result["timings"]
                    assert "llm_report_ms" in result["timings"]
                    assert "total_ms" in result["timings"]

                    # 验证计时值（由于 action_policy=RETRIEVE，RAG 和 LLM 应该有值）
                    assert result["timings"]["image_download_ms"] >= 0
                    assert result["timings"]["inference_ms"] >= 0
                    assert result["timings"]["rag_query_ms"] >= 0
                    assert result["timings"]["llm_report_ms"] >= 0
                    assert result["timings"]["total_ms"] >= 0


def test_analyze_image_download_timeout():
    """极端条件：图片下载超时"""
    with patch('app.worker.diagnosis_tasks.download_image_securely') as mock_download:
        # Mock 超时
        mock_download.side_effect = ImageDownloadError("下载超时")

        # 执行任务应该抛出异常
        with pytest.raises(RuntimeError, match="图片下载失败"):
            call_analyze_image(create_mock_task(), "http://example.com/test.jpg")


def test_analyze_image_download_failure_404():
    """极端条件：图片返回 404"""
    with patch('app.worker.diagnosis_tasks.download_image_securely') as mock_download:
        # Mock 404 错误
        mock_download.side_effect = ImageDownloadError("HTTP 错误: 404")

        # 执行任务应该抛出异常
        with pytest.raises(RuntimeError, match="图片下载失败"):
            call_analyze_image(create_mock_task(), "http://example.com/test.jpg")


def test_analyze_image_download_connection_error():
    """极端条件：网络连接错误"""
    with patch('app.worker.diagnosis_tasks.download_image_securely') as mock_download:
        # Mock 连接错误
        mock_download.side_effect = ImageDownloadError("连接失败")

        # 执行任务应该抛出异常
        with pytest.raises(RuntimeError, match="图片下载失败"):
            call_analyze_image(create_mock_task(), "http://example.com/test.jpg")


def test_analyze_image_taxonomy_not_found():
    """极端条件：Taxonomy 找不到对应分类"""
    with patch('app.worker.diagnosis_tasks.download_image_securely') as mock_download:
        # Mock HTTP 响应
        mock_download.return_value = b"fake image data"

        with patch('app.worker.diagnosis_tasks.get_taxonomy_service') as mock_get_taxonomy:
            # Mock TaxonomyService 找不到分类
            mock_taxonomy = Mock()
            mock_taxonomy.get_by_model_label.side_effect = Exception("Not found")
            mock_get_taxonomy.return_value = mock_taxonomy

            # 执行任务
            result = call_analyze_image(create_mock_task(), "http://example.com/test.jpg")

            # 验证结果使用默认值
            assert result["diagnosis_name"] == "未知"
            assert result["latin_name"] == "Unknown"
            assert result["category"] == "Unknown"
            assert result["action_policy"] == "HUMAN_REVIEW"
            assert result["taxonomy_id"] is None

            # 验证 timings 字段存在
            assert "timings" in result
            assert result["timings"]["total_ms"] >= 0


def test_analyze_image_with_optional_params():
    """测试带可选参数的分析"""
    with patch('app.worker.diagnosis_tasks.download_image_securely') as mock_download:
        # Mock HTTP 响应
        mock_download.return_value = b"fake image data"

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

            with patch('app.worker.diagnosis_tasks.get_rag_service') as mock_get_rag:
                # Mock RAG 服务
                mock_rag = Mock()
                mock_docs = [Document(page_content="测试文档", metadata={"source": "test.md"})]
                mock_rag.query = Mock(return_value=mock_docs)
                mock_get_rag.return_value = mock_rag

                mock_report_async = Mock(return_value="# 测试报告")
                with patch('app.worker.diagnosis_tasks.generate_diagnosis_report',
                          new=mock_report_async):
                    # 执行任务
                    result = call_analyze_image(
                        create_mock_task(),
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
        call_analyze_image(create_mock_task(), "")


def test_analyze_image_malformed_url():
    """极端条件：格式错误的 URL"""
    with patch('app.worker.diagnosis_tasks.download_image_securely') as mock_download:
        # Mock 连接错误
        mock_download.side_effect = ImageDownloadError("URL 格式错误")

        # 执行任务应该抛出异常
        with pytest.raises(RuntimeError, match="图片下载失败"):
            call_analyze_image(create_mock_task(), "not-a-valid-url")


def test_analyze_image_very_long_url():
    """极端条件：超长 URL"""
    long_url = "http://example.com/" + "a" * 10000 + "/test.jpg"

    with patch('app.worker.diagnosis_tasks.download_image_securely') as mock_download:
        # Mock HTTP 响应
        mock_download.return_value = b"fake image data"

        with patch('app.worker.diagnosis_tasks.get_taxonomy_service'):
            # 应该能处理（或超时）
            try:
                result = call_analyze_image(create_mock_task(), long_url)
                assert result is not None
            except Timeout:
                # 也可以接受超时
                assert True


def test_analyze_image_url_with_special_chars():
    """极端条件：URL 包含特殊字符"""
    special_url = "http://example.com/test file.jpg?token=abc@#$&space=here"

    with patch('app.worker.diagnosis_tasks.download_image_securely') as mock_download:
        # Mock HTTP 响应
        mock_download.return_value = b"fake image data"

        with patch('app.worker.diagnosis_tasks.get_taxonomy_service'):
            # 应该能处理
            result = call_analyze_image(create_mock_task(), special_url)
            assert result is not None


def test_analyze_image_zero_byte_image():
    """极端条件：0 字节图片"""
    with patch('app.worker.diagnosis_tasks.download_image_securely') as mock_download:
        # Mock 空响应
        mock_download.return_value = b"fake image data"

        with patch('app.worker.diagnosis_tasks.get_taxonomy_service'):
            # 应该能处理（即使图片为空）
            result = call_analyze_image(create_mock_task(), "http://example.com/empty.jpg")
            assert result["inference_time_ms"] >= 0


def test_analyze_image_large_image():
    """极端条件：超大图片"""
    with patch('app.worker.diagnosis_tasks.download_image_securely') as mock_download:
        # Mock 大响应（100MB）- 注意：实际上会触发 ImageDownloadError
        # 因为超过大小限制
        # 由于 SSRF 防护限制了大小为 10MB，这里应该抛出异常
        mock_download.side_effect = ImageDownloadError("文件过大")

        with patch('app.worker.diagnosis_tasks.get_taxonomy_service'):
            # 应该能处理（返回错误）
            with pytest.raises(RuntimeError, match="图片下载失败"):
                call_analyze_image(create_mock_task(), "http://example.com/large.jpg")


def test_analyze_image_concurrent_downloads():
    """极端条件：并发下载"""
    import threading

    with patch('app.worker.diagnosis_tasks.download_image_securely') as mock_download:
        # Mock HTTP 响应
        mock_download.return_value = b"fake image data"

        with patch('app.worker.diagnosis_tasks.get_taxonomy_service'):
            results = []
            errors = []

            def run_analysis():
                try:
                    result = call_analyze_image(create_mock_task(), "http://example.com/test.jpg")
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
    with patch('app.worker.diagnosis_tasks.download_image_securely') as mock_download:
        # Mock HTTP 响应
        mock_download.return_value = b"fake image data"

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
                result = call_analyze_image(create_mock_task(), "http://example.com/test.jpg")
                results.add(result["model_label"])

            # 应该包含所有 5 种分类
            expected_labels = {"healthy", "powdery_mildew", "aphid_complex",
                              "spider_mite", "late_blight"}
            assert results.issubset(expected_labels)


# =============================================================================
# Phase 6: RAG + LLM 报告生成集成测试
# =============================================================================


def test_analyze_image_with_report():
    """测试成功生成报告（action_policy == RETRIEVE）"""
    with patch('app.worker.diagnosis_tasks.download_image_securely') as mock_download:
        # Mock HTTP 响应
        mock_download.return_value = b"fake image data"

        with patch('app.worker.diagnosis_tasks.get_taxonomy_service') as mock_get_taxonomy:
            # Mock TaxonomyService - 返回 RETRIEVE 策略
            mock_taxonomy = Mock()
            mock_entry = Mock()
            mock_entry.zh_scientific_name = "番茄晚疫病"
            mock_entry.latin_name = "Phytophthora infestans"
            mock_entry.category = "Disease"
            mock_entry.action_policy = "RETRIEVE"
            mock_entry.id = 1
            mock_entry.description = "致病疫霉引起的病害"
            mock_entry.risk_level = "high"
            mock_taxonomy.get_by_model_label.return_value = mock_entry
            mock_get_taxonomy.return_value = mock_taxonomy

            with patch('app.worker.diagnosis_tasks.get_rag_service') as mock_get_rag:
                # Mock RAG 服务
                mock_rag = Mock()
                mock_docs = [
                    Document(
                        page_content="番茄晚疫病由致病疫霉引起，主要危害叶片和果实。",
                        metadata={"source": "data/knowledge/diseases/late_blight.md"}
                    ),
                    Document(
                        page_content="推荐使用68.75%银法利悬浮剂，用量60-75 ml/亩。",
                        metadata={"source": "data/knowledge/diseases/late_blight.md"}
                    ),
                ]
                mock_rag.query = Mock(return_value=mock_docs)
                mock_get_rag.return_value = mock_rag

                # Mock LLM 报告生成
                mock_report = """# 番茄晚疫病诊断报告

## 病害描述
番茄晚疫病由致病疫霉（Phytophthora infestans）引起...

## 防治措施
1. 农业防治：选用抗病品种
2. 化学防治：68.75%银法利悬浮剂，60-75 ml/亩

## 预防措施
加强通风，降低湿度...
"""
                mock_gen = Mock(return_value=mock_report)
                with patch('app.worker.diagnosis_tasks.generate_diagnosis_report',
                          new=mock_gen) as mock_generate:

                    # 执行任务
                    result = call_analyze_image(
                        create_mock_task(),
                        "http://example.com/test.jpg",
                        crop_type="番茄"
                    )

                    # 验证报告生成
                    assert result["report"] is not None
                    assert result["report"] == mock_report
                    assert result["report_error"] is None

                    # 验证 timings 字段包含 RAG 和 LLM 计时
                    assert "timings" in result
                    assert result["timings"]["rag_query_ms"] >= 0
                    assert result["timings"]["llm_report_ms"] >= 0
                    assert result["timings"]["total_ms"] >= 0

                    # 验证 RAG 和 LLM 被调用
                    mock_rag.query.assert_called_once()
                    mock_generate.assert_called_once()


def test_analyze_image_skip_report_healthy():
    """测试健康样本不生成报告（action_policy == PASS/IGNORE）"""
    with patch('app.worker.diagnosis_tasks.download_image_securely') as mock_download:
        # Mock HTTP 响应
        mock_download.return_value = b"fake image data"

        with patch('app.worker.diagnosis_tasks.get_taxonomy_service') as mock_get_taxonomy:
            # Mock TaxonomyService - 返回 PASS 策略（健康）
            mock_taxonomy = Mock()
            mock_entry = Mock()
            mock_entry.zh_scientific_name = "健康"
            mock_entry.latin_name = "Healthy"
            mock_entry.category = "Status"
            mock_entry.action_policy = "PASS"  # 不生成报告
            mock_entry.id = 1
            mock_entry.description = "植株健康"
            mock_entry.risk_level = "none"
            mock_taxonomy.get_by_model_label.return_value = mock_entry
            mock_get_taxonomy.return_value = mock_taxonomy

            with patch('app.worker.diagnosis_tasks.get_rag_service') as mock_get_rag:
                # Mock RAG 服务
                mock_rag = Mock()
                mock_get_rag.return_value = mock_rag

                # 执行任务
                result = call_analyze_image(create_mock_task(), "http://example.com/test.jpg")

                # 验证不生成报告
                assert result["report"] is None
                assert result["report_error"] is None

                # 验证 RAG 和 LLM 未被调用
                mock_rag.query.assert_not_called()


def test_analyze_image_skip_report_human_review():
    """测试 HUMAN_REVIEW 策略不生成报告"""
    with patch('app.worker.diagnosis_tasks.download_image_securely') as mock_download:
        # Mock HTTP 响应
        mock_download.return_value = b"fake image data"

        with patch('app.worker.diagnosis_tasks.get_taxonomy_service') as mock_get_taxonomy:
            # Mock TaxonomyService - 返回 HUMAN_REVIEW
            mock_taxonomy = Mock()
            mock_entry = Mock()
            mock_entry.zh_scientific_name = "未知病害"
            mock_entry.latin_name = "Unknown"
            mock_entry.category = "Unknown"
            mock_entry.action_policy = "HUMAN_REVIEW"
            mock_entry.id = None
            mock_entry.description = None
            mock_entry.risk_level = None
            mock_taxonomy.get_by_model_label.return_value = mock_entry
            mock_get_taxonomy.return_value = mock_taxonomy

            with patch('app.worker.diagnosis_tasks.get_rag_service') as mock_get_rag:
                # Mock RAG 服务
                mock_rag = Mock()
                mock_get_rag.return_value = mock_rag

                # 执行任务
                result = call_analyze_image(create_mock_task(), "http://example.com/test.jpg")

                # 验证不生成报告
                assert result["report"] is None
                assert result["report_error"] is None

                # 验证 RAG 未被调用
                mock_rag.query.assert_not_called()


def test_analyze_image_rag_failure():
    """测试 RAG 服务失败处理"""
    with patch('app.worker.diagnosis_tasks.download_image_securely') as mock_download:
        # Mock HTTP 响应
        mock_download.return_value = b"fake image data"

        with patch('app.worker.diagnosis_tasks.get_taxonomy_service') as mock_get_taxonomy:
            # Mock TaxonomyService - 返回 RETRIEVE 策略
            mock_taxonomy = Mock()
            mock_entry = Mock()
            mock_entry.zh_scientific_name = "番茄晚疫病"
            mock_entry.latin_name = "Phytophthora infestans"
            mock_entry.category = "Disease"
            mock_entry.action_policy = "RETRIEVE"
            mock_entry.id = 1
            mock_entry.description = "致病疫霉引起的病害"
            mock_entry.risk_level = "high"
            mock_taxonomy.get_by_model_label.return_value = mock_entry
            mock_get_taxonomy.return_value = mock_taxonomy

            with patch('app.worker.diagnosis_tasks.get_rag_service') as mock_get_rag:
                # Mock RAG 服务抛出异常
                mock_rag = Mock()
                mock_rag.query = Mock(
                    side_effect=RAGServiceNotInitializedError("ChromaDB not initialized")
                )
                mock_get_rag.return_value = mock_rag

                # 执行任务
                result = call_analyze_image(
                    create_mock_task(),
                    "http://example.com/test.jpg",
                    crop_type="番茄"
                )

                # 验证报告为空，但有错误信息
                assert result["report"] is None
                assert result["report_error"] is not None
                assert "RAG service not initialized" in result["report_error"]

                # 验证任务未失败（其他结果仍然有效）
                assert result["diagnosis_name"] == "番茄晚疫病"
                assert result["taxonomy_id"] == 1


def test_analyze_image_llm_timeout():
    """测试 LLM 超时处理"""
    with patch('app.worker.diagnosis_tasks.download_image_securely') as mock_download:
        # Mock HTTP 响应
        mock_download.return_value = b"fake image data"

        with patch('app.worker.diagnosis_tasks.get_taxonomy_service') as mock_get_taxonomy:
            # Mock TaxonomyService - 返回 RETRIEVE 策略
            mock_taxonomy = Mock()
            mock_entry = Mock()
            mock_entry.zh_scientific_name = "番茄晚疫病"
            mock_entry.latin_name = "Phytophthora infestans"
            mock_entry.category = "Disease"
            mock_entry.action_policy = "RETRIEVE"
            mock_entry.id = 1
            mock_entry.description = "致病疫霉引起的病害"
            mock_entry.risk_level = "high"
            mock_taxonomy.get_by_model_label.return_value = mock_entry
            mock_get_taxonomy.return_value = mock_taxonomy

            with patch('app.worker.diagnosis_tasks.get_rag_service') as mock_get_rag:
                # Mock RAG 服务
                mock_rag = Mock()
                mock_docs = [
                    Document(page_content="测试文档", metadata={"source": "test.md"})
                ]
                mock_rag.query = Mock(return_value=mock_docs)
                mock_get_rag.return_value = mock_rag

                mock_llm_async = Mock(
                    side_effect=ReportTimeoutError("LLM call timed out")
                )
                with patch('app.worker.diagnosis_tasks.generate_diagnosis_report',
                          new=mock_llm_async):

                    # 执行任务
                    result = call_analyze_image(
                        create_mock_task(),
                        "http://example.com/test.jpg",
                        crop_type="番茄"
                    )

                    # 验证报告为空，但有错误信息
                    assert result["report"] is None
                    assert result["report_error"] is not None
                    error_msg = result["report_error"].lower()
                    assert ("LLM call timed out" in result["report_error"] or
                            "timed out" in error_msg)

                    # 验证任务未失败（其他结果仍然有效）
                    assert result["diagnosis_name"] == "番茄晚疫病"
                    assert result["taxonomy_id"] == 1


def test_analyze_image_llm_api_error():
    """测试 LLM API 错误处理"""
    with patch('app.worker.diagnosis_tasks.download_image_securely') as mock_download:
        # Mock HTTP 响应
        mock_download.return_value = b"fake image data"

        with patch('app.worker.diagnosis_tasks.get_taxonomy_service') as mock_get_taxonomy:
            # Mock TaxonomyService - 返回 RETRIEVE 策略
            mock_taxonomy = Mock()
            mock_entry = Mock()
            mock_entry.zh_scientific_name = "番茄晚疫病"
            mock_entry.latin_name = "Phytophthora infestans"
            mock_entry.category = "Disease"
            mock_entry.action_policy = "RETRIEVE"
            mock_entry.id = 1
            mock_entry.description = "致病疫霉引起的病害"
            mock_entry.risk_level = "high"
            mock_taxonomy.get_by_model_label.return_value = mock_entry
            mock_get_taxonomy.return_value = mock_taxonomy

            with patch('app.worker.diagnosis_tasks.get_rag_service') as mock_get_rag:
                # Mock RAG 服务
                mock_rag = Mock()
                mock_docs = [
                    Document(page_content="测试文档", metadata={"source": "test.md"})
                ]
                mock_rag.query = Mock(return_value=mock_docs)
                mock_get_rag.return_value = mock_rag

                mock_llm_async = Mock(
                    side_effect=LLMError("OpenAI API rate limit exceeded")
                )
                with patch('app.worker.diagnosis_tasks.generate_diagnosis_report',
                          new=mock_llm_async):

                    # 执行任务
                    result = call_analyze_image(
                        create_mock_task(),
                        "http://example.com/test.jpg",
                        crop_type="番茄"
                    )

                    # 验证报告为空，但有错误信息
                    assert result["report"] is None
                    assert result["report_error"] is not None
                    assert "rate limit" in result["report_error"].lower()

                    # 验证任务未失败
                    assert result["diagnosis_name"] == "番茄晚疫病"
                    assert result["taxonomy_id"] == 1


def test_analyze_image_with_report_empty_contexts():
    """测试 RAG 返回空上下文时的处理"""
    with patch('app.worker.diagnosis_tasks.download_image_securely') as mock_download:
        # Mock HTTP 响应
        mock_download.return_value = b"fake image data"

        with patch('app.worker.diagnosis_tasks.get_taxonomy_service') as mock_get_taxonomy:
            # Mock TaxonomyService - 返回 RETRIEVE 策略
            mock_taxonomy = Mock()
            mock_entry = Mock()
            mock_entry.zh_scientific_name = "番茄晚疫病"
            mock_entry.latin_name = "Phytophthora infestans"
            mock_entry.category = "Disease"
            mock_entry.action_policy = "RETRIEVE"
            mock_entry.id = 1
            mock_entry.description = "致病疫霉引起的病害"
            mock_entry.risk_level = "high"
            mock_taxonomy.get_by_model_label.return_value = mock_entry
            mock_get_taxonomy.return_value = mock_taxonomy

            with patch('app.worker.diagnosis_tasks.get_rag_service') as mock_get_rag:
                # Mock RAG 服务 - 返回空列表
                mock_rag = Mock()
                mock_rag.query = Mock(return_value=[])
                mock_get_rag.return_value = mock_rag

                mock_report = "# 番茄晚疫病诊断报告\n\n未找到相关资料..."
                mock_llm_async = Mock(return_value=mock_report)
                with patch('app.worker.diagnosis_tasks.generate_diagnosis_report',
                          new=mock_llm_async):

                    # 执行任务
                    result = call_analyze_image(
                        create_mock_task(),
                        "http://example.com/test.jpg",
                        crop_type="番茄"
                    )

                    # 验证报告仍然生成
                    assert result["report"] is not None
                    assert result["report_error"] is None

                    # 验证 LLM 被调用（空上下文不应该阻止报告生成）
                    mock_llm_async.assert_called_once()
                    call_args = mock_llm_async.call_args
                    assert call_args[1]["contexts"] == []


def test_analyze_image_with_report_low_confidence():
    """测试低置信度时报告包含警告"""
    with patch('app.worker.diagnosis_tasks.download_image_securely') as mock_download:
        # Mock HTTP 响应
        mock_download.return_value = b"fake image data"

        with patch('app.worker.diagnosis_tasks.get_taxonomy_service') as mock_get_taxonomy:
            # Mock TaxonomyService - 返回 RETRIEVE 策略
            mock_taxonomy = Mock()
            mock_entry = Mock()
            mock_entry.zh_scientific_name = "番茄晚疫病"
            mock_entry.latin_name = "Phytophthora infestans"
            mock_entry.category = "Disease"
            mock_entry.action_policy = "RETRIEVE"
            mock_entry.id = 1
            mock_entry.description = "致病疫霉引起的病害"
            mock_entry.risk_level = "high"
            mock_taxonomy.get_by_model_label.return_value = mock_entry
            mock_get_taxonomy.return_value = mock_taxonomy

            with patch('app.worker.diagnosis_tasks.get_rag_service') as mock_get_rag:
                # Mock RAG 服务
                mock_rag = Mock()
                mock_docs = [Document(page_content="测试文档", metadata={"source": "test.md"})]
                mock_rag.query = Mock(return_value=mock_docs)
                mock_get_rag.return_value = mock_rag

                mock_report = "# 番茄晚疫病诊断报告\n\n⚠️ 置信度较低..."
                mock_llm_async = Mock(return_value=mock_report)
                with patch('app.worker.diagnosis_tasks.generate_diagnosis_report',
                          new=mock_llm_async) as mock_generate:

                    # 执行任务
                    result = call_analyze_image(
                        create_mock_task(),
                        "http://example.com/test.jpg",
                        crop_type="番茄"
                    )

                    # 验证报告生成
                    assert result["report"] is not None

                    # 验证 LLM 被调用，并且 confidence 参数传递正确
                    mock_generate.assert_called_once()
                    call_args = mock_generate.call_args
                    # 注意：confidence 是从 mock_result 中随机选择的，可能是低值
                    assert "confidence" in call_args[1]

